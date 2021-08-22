import speech_recognition as sr 
import sounddevice as sd
import pyttsx3
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from pydub import AudioSegment
from pydub.playback import play
from threading import Timer
import vosk
import sys
import os
import json
import queue
import requests
from utils import clean_text
import scapy.all as scapy
import socket
import argparse

class VirtualAssistantClient(object):
    
    def __init__(self, hub_ip, use_voice, synth_voice, google, watson, mic_tag, blocksize, samplerate, debug):
        self.USEVOICE = use_voice
        self.SYNTHVOICE = synth_voice
        self.WATSON = watson
        self.GOOGLE = google
        self.BLOCKSIZE = blocksize
        self.SAMPLERATE = samplerate
        self.DEBUG = debug

        self.log(f'Debug Mode: {self.DEBUG}')
        self.log(f'Use Voice Input: {self.USEVOICE}')
        self.log(f'Using GOOGLE: {self.GOOGLE}')
        self.log(f'Synth Voice Output: {self.USEVOICE}')
        self.log(f'Using WATSON: {self.WATSON}')

        port = 8000
        if not hub_ip:
            devices = self.scan('10.0.0.1/24')
            self.log(devices)
            self.log('Looking for VA HUB...')
            for device in devices:
                ip = device['ip']
                self.log(f'\rTesting: {ip}', end='')
                try:
                    response = requests.get(f'http://{ip}:{port}/is_va_hub').json()
                    host = ip
                    break
                except:
                    pass
        else:
            host = hub_ip

        self.log(f'\nFound VA HUB | ip: {host}')

        self.api_url = f'http://{host}:{port}'
        name_and_address = requests.get(f'{self.api_url}/get_name_and_address').json()
        self.NAME = name_and_address['name']
        self.ADDRESS = name_and_address['address']

        self.vosk_model = vosk.Model('vosk_small')
        self.vosk_que = queue.Queue()

        self.recog = sr.Recognizer()
        devices = sr.Microphone.list_microphone_names()
        self.log(devices)
        if not mic_tag:
            mic_tag='microphone'
        output = [idx for idx, element in enumerate(devices) if mic_tag in element.lower()]
        self.device = output[0]
        self.log(f'Device {devices[self.device]} index {self.device}')
        self.mic = sr.Microphone(device_index = self.device)
        with self.mic as source:
            self.recog.adjust_for_ambient_noise(source)

        device_info = sd.query_devices(self.device, 'input')
        if self.SAMPLERATE is None:
            self.SAMPLERATE = int(device_info['default_samplerate'])

        self.log(self.SAMPLERATE)

        if self.WATSON:
            authenticator = IAMAuthenticator(os.environ['IBM_API_KEY'])
            self.text_to_speech = TextToSpeechV1(
                authenticator=authenticator
            )
            self.text_to_speech.set_service_url('https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/558fb7c3-30e9-4fe7-8861-46cd1031caf9')

        else:
            self.tts = pyttsx3.init()
            self.tts.setProperty('voice', 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_enGB_GeorgeM')
            self.tts.setProperty('rate',175)
    
        self.ENGAGED = True
        self.HOT = False
        self.TIMEOUT = 15.0
        self.TIMER = Timer(interval=30.0, function=self.disengage)
        if self.USEVOICE:
            self.TIMER.start()

        self.say(f'How can I help {self.ADDRESS}?')

        self.stop_listening = self.recog.listen_in_background(self.mic, self.listen_callback)

    def log(self, log_text, end='\n'):
        if self.DEBUG:
            print(log_text, end=end)

    
    def scan(self, ip):
        arp_req_frame = scapy.ARP(pdst = ip)

        broadcast_ether_frame = scapy.Ether(dst = "ff:ff:ff:ff:ff:ff")
        
        broadcast_ether_arp_req_frame = broadcast_ether_frame / arp_req_frame

        answered_list = scapy.srp(broadcast_ether_arp_req_frame, timeout = 1, verbose = False)[0]
        result = []
        for i in range(0,len(answered_list)):
            client_dict = {"ip" : answered_list[i][1].psrc, "mac" : answered_list[i][1].hwsrc}
            result.append(client_dict)

        return result

    def vosk_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            self.log(status, file=sys.stderr)
        self.vosk_que.put(bytes(indata))

    def listen_callback(self, recognizer, audio):
        self.log(f'callback {self.HOT}')
        if self.HOT or self.ENGAGED:
            '''
            print('Saving...')
            with open("microphone-results.wav", "wb") as f:
                f.write(audio.get_wav_data())
            print('Saved')
            '''
            self.log('Transcribing...')
            files = {'audio_file': audio.get_wav_data()}
            response = requests.post(
                'http://10.0.0.120:8000/understand_from_audio',
                files=files
            )
            if response.status_code == 200:
                understanding = response.json()
                self.log(f'Response: {understanding}')
                self.decide_from_understanding(understanding)
            self.HOT = False
    
    def shutdown(self):
        print('Shutdown...')
        self.TIMER.cancel()
        sys.exit(0)

    def say(self, text):
        print(f'{self.NAME}: {text}')
        if self.SYNTHVOICE:
            with open('./response.wav', 'wb') as audio_file:
                if self.WATSON:
                    audio_file.write(
                        self.text_to_speech.synthesize(
                            text,
                            voice='en-GB_JamesV3Voice',
                            accept='audio/wav'        
                        ).get_result().content)
                else:
                    audio_file.write(
                        requests.get(f'{self.api_url}/synth_voice/{text}').content
                    )

            audio = AudioSegment.from_wav('response.wav')
            play(audio)
    
    def understand_from_google(self):
        text = ''
        while True:
            while True:
                with self.mic as source:
                    self.recog.adjust_for_ambient_noise(source)
                    audio = self.recog.listen(source)
                    try:
                        text = self.recog.recognize_google(audio)
                        #print(text)
                        break
                    except Exception as e:
                        print(e)
                        pass

            if text:
                text = clean_text(text)
                self.log(f'cleaned: {text}')
                if self.NAME in text or self.ENGAGED:
                    self.stop_waiting()
                    understanding = requests.get(f'{self.api_url}/understand/{text}').json()
                    self.decide_from_understanding(understanding)
        
    def understand_from_hotword(self):
        with sd.RawInputStream(samplerate=self.SAMPLERATE, blocksize = self.BLOCKSIZE, device=self.device, dtype='int16',
                                    channels=1, callback=self.vosk_callback):

            rec = vosk.KaldiRecognizer(self.vosk_model, self.SAMPLERATE, f'["{self.NAME}", "[unk]"]')
            while True:
                data = self.vosk_que.get()
                if rec.AcceptWaveform(data):
                    text = rec.Result()
                else:
                    text = json.loads(rec.PartialResult())['partial']
                    if self.NAME in text and not self.HOT:
                        self.log('Hotword')
                        self.HOT = True
                        self.log('Listening...')

    def decide_from_understanding(self, understanding):
        response = understanding['response']
        intent = understanding['intent']
        conf = understanding['conf']
        self.log(f'intent: {intent} - conf: {conf} - resp: {response}')

        if response:
            self.say(response)
            self.wait_for_response()
        
        if intent == 'shutdown':
            self.shutdown()
    
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
        try:
            if self.USEVOICE:
                self.log('Listening...')
                if self.GOOGLE:
                    self.understand_from_google()
                else:
                    self.understand_from_hotword()
            else:
                while True:
                    text = input('You: ')
                    understanding = requests.get(f'{self.api_url}/understand/{text}').json()
                    self.decide_from_understanding(understanding)

        except Exception as ex:
                self.log(ex)
                self.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--hub', type=str, help='VA hub ip address', default='')
    parser.add_argument('--useVoice', help='Use voice as input', action='store_true')
    parser.add_argument('--synthVoice', help='Synthesize voice as output', action='store_true')
    parser.add_argument('--google', help='Use google speech recognition', action='store_true')
    parser.add_argument('--watson', help='Use watson speech synthesis', action='store_true')
    parser.add_argument('--mic', type=str, help='Microphone tag', default='')
    parser.add_argument('--blocksize', type=int, help='Blocksize for voice capture', default=8000)
    parser.add_argument('--samplerate', type=int, help='Samplerate for microphone', default=None)
    parser.add_argument('--debug', help='Synthesize voice as output', action='store_true')

    args = parser.parse_args()
    assistant = VirtualAssistantClient(*vars(args).values())
    assistant.run()    