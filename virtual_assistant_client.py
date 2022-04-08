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
import wave
import base64
import paho.mqtt.client as mqtt
import logging
from skills import volume_control

class VirtualAssistantClient(threading.Thread):
    
    def __init__(self):

        self.load_config()

        logging.basicConfig(filename='va_client.log', encoding='utf-8', level=logging.DEBUG if self.DEBUG else logging.WARNING)

        if not self.HUB_IP:
            self.log('Auto-Discover VA HUB...')
            self.config['hubIp'] = self.scan_for_hub(self.HUB_PORT)
            self.HUB_IP = self.config['hubIp']
            self.save_config()

        self.log(f'VA HUB Found | IP: {self.HUB_IP}')

        # Get hub info
        self.api_url = f'http://{self.HUB_IP}:{self.HUB_PORT}'
        hub_response = requests.get(f'{self.api_url}/get_hub_details').json()
        self.NAME = hub_response['name']
        self.ADDRESS = hub_response['address']

        # MQTT client
        mqtt_hostname = hub_response['mqtt_broker_ip']
        mqtt_port = hub_response['mqtt_broker_port']
        mqtt_user = hub_response['mqtt_broker_user']
        mqtt_pswd = hub_response['mqtt_broker_pswd']
        self.mqtt_client = mqtt.Client(self.ROOM_ID, clean_session=True)
        
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.username_pw_set(username=mqtt_user, password=mqtt_pswd)

        self.mqtt_client.connect(mqtt_hostname, mqtt_port)
        self.mqtt_client.loop_start()

        # Mic and speaker setup
        microphones = sr.Microphone.list_microphone_names()
        self.log(microphones)
        if not self.MIC_TAG:
            self.MIC_TAG='microphone'
        self.mic_index = [idx for idx, element in enumerate(microphones) if self.MIC_TAG in element.lower()][0]
        self.mic = microphones[self.mic_index]
        self.log(f'Device {self.mic} index {self.mic_index}')

        mic_info = sd.query_devices(self.mic_index, 'input')
        if self.SAMPLERATE is None:
            self.SAMPLERATE = int(mic_info['default_samplerate'])

        # Activity timer
        self.ENGAGED = True
        self.LISTENING = True
        self.TIMER = Timer(interval=self.ACTIVITY_TIMEOUT*2, function=self.disengage)
        if self.USE_VOICE:
            self.TIMER.start()

        self.record_queue = queue.Queue()
        
        self.log(f'Room ID: {self.ROOM_ID }')
        self.log(f'Debug Mode: {self.DEBUG}')
        self.log(f'Use Voice Input: {self.USE_VOICE}')
        self.log(f'Mic Index: {self.mic_index}')
        self.log('Offline Speech Recognition' if self.OFFLINE_SR else 'Online Speech Recognition')
        self.log(f'Synth Voice Output: {self.SYNTH_VOICE}')
        self.log(f'RPI: {self.RPI}')
        self.log(f'Samplerate: {self.SAMPLERATE}')
        self.log(f'Blocksize: {self.BLOCKSIZE}')
        self.log(f'Activity Timeout: {self.ACTIVITY_TIMEOUT}')

        self.synth_and_say(f'How can I help {self.ADDRESS}?')

        self.callback = ''
        
        self.skills = {
            'set_volume':volume_control.set_volume
        }

    def load_config(self):
        self.config = json.load(open('client_config.json', 'r'))
        
        self.ROOM_ID = self.config['room']
        self.HUB_IP = self.config['hubIp']
        self.HUB_PORT = self.config['hubPort']
        self.USE_VOICE = self.config['useVoice']
        self.SYNTH_VOICE = self.config['synthVoice']
        self.OFFLINE_SR = self.config['offlineSR']
        self.MIC_TAG = self.config['mic']
        self.BLOCKSIZE = self.config['blocksize']
        self.SAMPLERATE = self.config['samplerate']
        self.ACTIVITY_TIMEOUT = self.config['activityTimeout']
        self.SPEAKER_INDEX = self.config['speakerIndex']
        self.DEBUG = self.config['debug']
        self.RPI = self.config['rpi']

    def save_config(self):
        with open('client_config.json', 'w') as outfile:
            json.dump(self.config, outfile)

    def scan_for_hub(self, port):
        while True:
            devices = net_scan('10.0.0.1/24')
            self.log('Looking for VA HUB...')
            for device in devices:
                ip = device['ip']
                try:
                    response = requests.get(f'http://{ip}:{port}/is_va_hub', timeout=5)
                    return ip
                except:
                    pass

    def log(self, log_text, end='\n'):
        logging.info(log_text)
        if self.DEBUG:
            print(log_text, end=end)
    
    def shutdown(self):
        self.log('Shutdown...')
        self.TIMER.cancel()
        sys.exit(0)

    def on_message(self, mosq, obj, msg):
        text = msg.payload.decode("utf-8") 
        self.log(f'MQTT said: {text}')
        self.LISTENING = False
        self.synth_and_say(text)
        self.LISTENING = True

    def on_connect(self, client, userdata, flags, rc):
        self.log(f'Connected with result code {str(rc)}')
        channel = f'home/virtual_assistant/room/{self.ROOM_ID}/say'
        self.mqtt_client.subscribe(channel)
        self.log(f'Subscribed to {channel}')

    def synth_and_say(self, text):
        self.log(f'{self.NAME}: {text}')
        if self.SYNTH_VOICE:
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
        self.log('Listening with hotword')

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
            with sd.InputStream(samplerate=self.SAMPLERATE, blocksize = 8000, device=self.mic_index, dtype='int16',
                                    channels=1, callback=input_stream_callback):

                #print('Listening...')

                rec = vosk.KaldiRecognizer(vosk_model, self.SAMPLERATE)
                audio_cache = []
                while self.LISTENING:
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
                if self.ENGAGED and self.LISTENING:
                    print(outFile)
                    self.understand_from_audio_and_synth(outFile)
            

    def understand_from_audio_and_synth(self, audio):
        files = {'samplerate': self.SAMPLERATE, 'callback': self.callback, 'audio_file': audio, 'room_id': self.ROOM_ID}
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
        response_text = response_packet['response_text']
        intent = understanding['intent']
        conf = understanding['conf']
        action = response_packet['action']
        self.callback = response_packet['callback']
        synth = base64.b64decode(understanding['synth'])
        self.log(f'intent: {intent} - conf: {conf} - resp: {response_text}')
        if response_packet:
            self.log(f'{self.NAME}: {response_text}')
            if self.SYNTH_VOICE:
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
            self.skills[method](data, self.SPEAKER_INDEX)
    
    def disengage(self):
        self.log('Disengaged')
        self.ENGAGED = False
        requests.get(f'{self.api_url}/reset_chat')

    def wait_for_response(self):
        if self.USE_VOICE:
            self.TIMER.cancel()
            self.log('Waiting for response')
            self.ENGAGED = True
            self.TIMER = Timer(interval=self.ACTIVITY_TIMEOUT, function=self.disengage)
            self.TIMER.start()

    def stop_waiting(self):
        self.TIMER.cancel()

    def run(self):
        if self.USE_VOICE:
            if not self.OFFLINE_SR:
                self.listen_with_google()
            else:
                self.listen_with_hotword()
        else:
            while True:
                text = input('You: ')
                self.understand_from_text_and_synth(text)

if __name__ == '__main__':
    assistant = VirtualAssistantClient()
    assistant.run()
