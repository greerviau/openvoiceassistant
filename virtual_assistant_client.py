import speech_recognition as sr 
import sounddevice as sd
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play
import threading
from threading import Timer
import vosk
import sys
import os
import json
import queue
import requests
from utils import clean_text, net_scan
import scapy.all as scapy
import wave
import base64
from skills import volume_control

class VirtualAssistantClient(threading.Thread):
    
    def __init__(self, node_id, hub_ip, use_voice, synth_voice, google, mic_tag, blocksize, samplerate, activityTimeout, speakerIndex, debug, rpi):
        self.NODE_ID = node_id.lower()
        self.USEVOICE = use_voice
        self.SYNTHVOICE = synth_voice
        self.GOOGLE = google
        self.BLOCKSIZE = blocksize
        self.SAMPLERATE = samplerate
        self.DEBUG = debug
        self.RPI = rpi

        port = 8000
        if not hub_ip:
            self.log('Auto-Discover VA HUB...')
            host = self.scan_for_hub(port)
        else:
            host = hub_ip

        self.log(f'\nVA HUB Found | IP: {host}')

        # Get hub info
        self.api_url = f'http://{host}:{port}'
        hub_response = requests.get(f'{self.api_url}/get_hub_details').json()
        self.NAME = hub_response['name']
        self.ADDRESS = hub_response['address']

        # MQTT client
        mqtt_hostname = hub_response['mqtt_broker_ip']
        mqtt_port = hub_response['mqtt_broker_port']
        self.mqtt_client = mqtt.Client(self.NODE_ID)
        self.client.on_message = self.on_message
        self.client.connect(mqtt_hostname, mqtt_port)
        self.client.subscribe(f'home/virtual_assistant/node/{id}/say')

        # Mic and speaker setup
        self.speaker = speakerIndex
        devices = sr.Microphone.list_microphone_names()
        self.log(devices)
        if not mic_tag:
            mic_tag='microphone'
        output = [idx for idx, element in enumerate(devices) if mic_tag in element.lower()]
        self.device = output[0]
        self.log(f'Device {devices[self.device]} index {self.device}')

        device_info = sd.query_devices(self.device, 'input')
        if self.SAMPLERATE is None:
            self.SAMPLERATE = int(device_info['default_samplerate'])

        # Activity timer
        self.ENGAGED = True
        self.HOT = False
        self.TIMEOUT = activityTimeout
        self.TIMER = Timer(interval=activityTimeout*2, function=self.disengage)
        if self.USEVOICE:
            self.TIMER.start()

        self.record_queue = queue.Queue()
        
        self.log(f'Debug Mode: {self.DEBUG}')
        self.log(f'Use Voice Input: {self.USEVOICE}')
        self.log(f'Device Index: {self.device}')
        self.log('Online Speech Recognition' if self.GOOGLE else 'Offline Speech Recognition')
        self.log(f'Synth Voice Output: {self.USEVOICE}')
        self.log(f'RPI: {self.RPI}')
        self.log(f'Samplerate: {self.SAMPLERATE}')
        self.log(f'Blocksize: {self.BLOCKSIZE}')
        self.log(f'Activity Timeout: {self.TIMEOUT}')

        self.synth_and_say(f'How can I help {self.ADDRESS}?')

        self.callback = ''
        
        self.skills = {
            'set_volume':volume_control.set_volume
        }

    def scan_for_hub(self, port):
        devices = net_scan('10.0.0.1/24')
        self.log(devices)
        self.log('Looking for VA HUB...')
        for device in devices:
            ip = device['ip']
            self.log(f'\rTesting: {ip}', end='')
            try:
                response = requests.get(f'http://{ip}:{port}/is_va_hub')
                return ip
            except:
                pass

    def log(self, log_text, end='\n'):
        if self.DEBUG:
            print(log_text, end=end)
    
    def shutdown(self):
        self.log('Shutdown...')
        self.TIMER.cancel()
        sys.exit(0)

    def on_message(self, mosq, obj, msg):
        self.synth_and_say(msg)

    def synth_and_say(self, text):
        self.log(f'{self.NAME}: {text}')
        if self.SYNTHVOICE:
            with open('./client_response.wav', 'wb') as audio_file:
                audio_file.write(
                    requests.get(f'{self.api_url}/synth_voice/{text}').content
                )

            self.say()

    def say(self):
        if not self.RPI:
            audio = AudioSegment.from_wav('client_response.wav')
            play(audio)
        else:
            os.system('aplay client_response.wav')

    def listen(self, source):
        self.log('Listening...')
        audio = self.recog.listen(source)
        self.log('Done Listening')
        return audio
                
    def listen_with_google(self):
        text = ''
        with self.mic as source:
            self.recog.adjust_for_ambient_noise(source)
            while True:
                while True:
                    audio = self.listen(source)
                    try:
                        text = self.recog.recognize_google(audio)
                        break
                    except Exception as e:
                        self.log(e)
                        pass
                if text:
                    text = clean_text(text)
                    self.log(f'cleaned: {text}')
                    if self.NAME in text or self.ENGAGED:
                        self.understand_from_text_and_synth(text)
        
    def listen_with_hotword(self):
        vosk_model = vosk.Model('vosk_small')
        rec = vosk.KaldiRecognizer(vosk_model, self.SAMPLERATE)

        def input_stream_callback(indata, frames, time, status):
            """This is called (from a separate thread) for each audio block."""
            if status:
                self.log(status, file=sys.stderr)
            self.record_queue.put(indata.copy())

        while True:
            self.vosk_queue = queue.Queue()
            self.record_queue = queue.Queue()
            #with sf.SoundFile('./client_command.wav', mode='w', samplerate=self.SAMPLERATE, subtype='PCM_16', channels=1) as outFile:
            outFile = []
            with sd.InputStream(samplerate=self.SAMPLERATE, blocksize = 8000, device=self.device, dtype='int16',
                                    channels=1, callback=input_stream_callback):

                #print('Listening...')

                rec = vosk.KaldiRecognizer(vosk_model, self.SAMPLERATE)
                audio_cache = []
                while True:
                    data = bytes(self.record_queue.get())
                    if rec.AcceptWaveform(data):
                        outFile.append(base64.b64encode(data).decode('utf-8'))
                        text = json.loads(rec.Result())['text']
                        self.log(text)
                        if self.NAME in text:
                            self.ENGAGED = True
                        break
                    else:
                        partial = json.loads(rec.PartialResult())['partial']
                        if partial:
                            for i in range(len(audio_cache)):
                                outFile.append(base64.b64encode(audio_cache.pop(0)).decode('utf-8'))
                            audio_cache = []
                            outFile.append(base64.b64encode(data).decode('utf-8'))
                        else:
                            audio_cache.append(data)
                            if len(audio_cache) > 5:
                                audio_cache.pop(0)
                if self.ENGAGED:
                    self.understand_from_audio_and_synth(outFile)
            

    def understand_from_audio_and_synth(self, audio):
        files = {'samplerate': self.SAMPLERATE, 'callback': self.callback, 'audio_file': audio, 'node_id': self.NODE_ID}
        response = requests.post(
            f'{self.api_url}/understand_from_audio_and_synth',
            json=files
        )
        if response.status_code == 200:
            understanding = response.json()
            self.process_understanding_and_say(understanding)

    def understand_from_text_and_synth(self, text):
        response = requests.get(f'{self.api_url}/understand_from_text_and_synth/{text}')
        if response.status_code == 200:
            understanding = response.json()
            self.process_understanding_and_say(understanding)

    def process_understanding_and_synth(self, understanding):
        response = understanding['response']
        intent = understanding['intent']
        conf = understanding['conf']
        self.log(f'intent: {intent} - conf: {conf} - resp: {response}')

        if response:
            self.log(f'{self.NAME}: {response}')
            self.synth_and_say(response)
            self.wait_for_response()
        
        if intent == 'shutdown':
            self.shutdown()

    def process_understanding_and_say(self, understanding):
        #self.stop_waiting()
        response_packet = understanding['response_packet']
        response_text = response_packet['reponse_text']
        intent = understanding['intent']
        conf = understanding['conf']
        action = response_packet['action']
        self.callback = response_packet['callback']
        synth = base64.b64decode(understanding['synth'])
        self.log(f'intent: {intent} - conf: {conf} - resp: {response_text}')
        if response_packet:
            self.log(f'{self.NAME}: {response_text}')
            if self.SYNTHVOICE:
                with open('./client_response.wav', 'wb') as audio_file:
                    audio_file.write(synth)
            if action:
                self.do_action(action)
            self.say()
            self.wait_for_response()
        
        if intent == 'shutdown':
            self.shutdown()

    def do_action(self, action):
        if self.RPI:
            method = action['method']
            data = action['data']
            self.skills[method](data, self.speaker)
    
    def disengage(self):
        self.log('Disengaged')
        self.ENGAGED = False
        requests.get(f'{self.api_url}/reset_chat')

    def wait_for_response(self):
        if self.USEVOICE:
            self.TIMER.cancel()
            self.log('Waiting for response')
            self.ENGAGED = True
            self.TIMER = Timer(interval=self.TIMEOUT, function=self.disengage)
            self.TIMER.start()

    def stop_waiting(self):
        self.TIMER.cancel()

    def run(self):
        if self.USEVOICE:
            if self.GOOGLE:
                self.listen_with_google()
            else:
                self.listen_with_hotword()
        else:
            while True:
                text = input('You: ')
                self.understand_from_text_and_synth(text)

if __name__ == '__main__':

    config = json.load(open('client_config.json', 'r'))

    assistant = VirtualAssistantClient(*config.values())
    assistant.run()
