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

        logging.basicConfig(filename='va_server.log', encoding='utf-8', level=logging.DEBUG if self.config['debug'] else logging.WARNING)

        if not self.HUB_IP:
            logging.info('Auto-Discover VA HUB...')
            self.config['hubIp'] = self.scan_for_hub(self.HUB_PORT)
            self.HUB_IP = self.config['hubIp']
            self.save_config()

        logging.info(f'VA HUB Found | IP: {self.HUB_IP}')

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
        devices = sr.Microphone.list_microphone_names()
        logging.info(devices)
        if not self.MIC_TAG:
            self.MIC_TAG='microphone'
        output = [idx for idx, element in enumerate(devices) if self.MIC_TAG in element.lower()]
        self.device = output[0]
        logging.info(f'Device {devices[self.device]} index {self.device}')

        device_info = sd.query_devices(self.device, 'input')
        if self.SAMPLERATE is None:
            self.SAMPLERATE = int(device_info['default_samplerate'])

        # Activity timer
        self.ENGAGED = True
        self.LISTENING = True
        self.TIMER = Timer(interval=self.ACTIVITY_TIMEOUT*2, function=self.disengage)
        if self.USE_VOICE:
            self.TIMER.start()

        self.record_queue = queue.Queue()
        
        logging.info(f'Room ID: {self.ROOM_ID }')
        logging.info(f'Debug Mode: {self.DEBUG}')
        logging.info(f'Use Voice Input: {self.USE_VOICE}')
        logging.info(f'Device Index: {self.device}')
        logging.info('Online Speech Recognition' if self.OFFLINE_SR else 'Offline Speech Recognition')
        logging.info(f'Synth Voice Output: {self.USE_VOICE}')
        logging.info(f'RPI: {self.RPI}')
        logging.info(f'Samplerate: {self.SAMPLERATE}')
        logging.info(f'Blocksize: {self.BLOCKSIZE}')
        logging.info(f'Activity Timeout: {self.ACTIVITY_TIMEOUT}')

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
            logging.info('Looking for VA HUB...')
            for device in devices:
                ip = device['ip']
                try:
                    response = requests.get(f'http://{ip}:{port}/is_va_hub', timeout=5)
                    return ip
                except:
                    pass

    def log(self, log_text, end='\n'):
        if self.DEBUG:
            print(log_text, end=end)
    
    def shutdown(self):
        logging.info('Shutdown...')
        self.TIMER.cancel()
        sys.exit(0)

    def on_message(self, mosq, obj, msg):
        text = msg.payload.decode("utf-8") 
        logging.info(f'MQTT said: {text}')
        self.LISTENING = False
        self.synth_and_say(text)
        self.LISTENING = True

    def on_connect(self, client, userdata, flags, rc):
        logging.info(f'Connected with result code {str(rc)}')
        channel = f'home/virtual_assistant/room/{self.ROOM_ID}/say'
        self.mqtt_client.subscribe(channel)
        logging.info(f'Subscribed to {channel}')

    def synth_and_say(self, text):
        logging.info(f'{self.NAME}: {text}')
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
        logging.info('Listening...')
        audio = self.recog.listen(source)
        logging.info('Done Listening')
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
                        logging.info(e)
                        pass
                if text:
                    text = clean_text(text)
                    logging.info(f'cleaned: {text}')
                    if self.NAME in text or self.ENGAGED:
                        self.understand_from_text_and_synth(text)
        
    def listen_with_hotword(self):
        vosk_model = vosk.Model('vosk_small')
        rec = vosk.KaldiRecognizer(vosk_model, self.SAMPLERATE)

        def input_stream_callback(indata, frames, time, status):
            """This is called (from a separate thread) for each audio block."""
            if status:
                logging.info(status, file=sys.stderr)
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
                while self.LISTENING:
                    data = bytes(self.record_queue.get())
                    if rec.AcceptWaveform(data):
                        outFile.append(base64.b64encode(data).decode('utf-8'))
                        text = json.loads(rec.Result())['text']
                        logging.info(text)
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
                    self.understand_from_audio_and_synth(outFile)
            

    def understand_from_audio_and_synth(self, audio):
        files = {'samplerate': self.SAMPLERATE, 'callback': self.callback, 'audio_file': audio, 'ROOM_ID': self.ROOM_ID}
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
        logging.info(f'intent: {intent} - conf: {conf} - resp: {response}')

        if response:
            logging.info(f'{self.NAME}: {response}')
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
        logging.info(f'intent: {intent} - conf: {conf} - resp: {response_text}')
        if response_packet:
            logging.info(f'{self.NAME}: {response_text}')
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
            self.skills[method](data, self.SPEAKER_INDEX)
    
    def disengage(self):
        logging.info('Disengaged')
        self.ENGAGED = False
        requests.get(f'{self.api_url}/reset_chat')

    def wait_for_response(self):
        if self.USE_VOICE:
            self.TIMER.cancel()
            logging.info('Waiting for response')
            self.ENGAGED = True
            self.TIMER = Timer(interval=self.ACTIVITY_TIMEOUT, function=self.disengage)
            self.TIMER.start()

    def stop_waiting(self):
        self.TIMER.cancel()

    def run(self):
        if self.USE_VOICE:
            if self.OFFLINE_SR:
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
