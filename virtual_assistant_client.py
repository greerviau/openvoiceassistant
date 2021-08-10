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
    
    def __init__(self, hub_ip = None, google=False, watson=False):
        port = 8000
        if not hub_ip:
            devices = self.scan('10.0.0.1/24')
            print(devices)
            print('Looking for VA HUB...')
            for device in devices:
                ip = device['ip']
                print(f'\rTesting: {ip}', end='')
                try:
                    response = requests.get(f'http://{ip}:{port}/is_va_hub')
                    host = ip
                    break
                except:
                    pass
        else:
            host = hub_ip

        print(f'\nFound VA HUB | ip: {host}')
        self.api_url = f'http://{host}:{port}'
        name_and_address = requests.get(f'{self.api_url}/get_name_and_address').json()
        self.NAME = name_and_address['name']
        self.ADDRESS = name_and_address['address']

        self.USEVOICE = True
        self.SYNTHVOICE = True
        self.WATSON = watson
        self.GOOGLE = google

        self.ENGAGED = True
        self.TIMEOUT = 15.0
        self.TIMER = Timer(interval=30.0, function=self.disengage)
        if self.USEVOICE:
            self.TIMER.start()

        self.vosk_model = vosk.Model('vosk')
        self.vosk_que = queue.Queue()

        self.recog = sr.Recognizer()
        devices = sr.Microphone.list_microphone_names()
        print(devices)
        output = [idx for idx, element in enumerate(devices) if 'snowball' in element.lower() or 'microphone' in element.lower()]
        self.device = output[0]
        print(f'Device {devices[self.device]} index {self.device}')
        self.mic = sr.Microphone(device_index = self.device)

        device_info = sd.query_devices(self.device, 'input')
        self.samplerate = int(device_info['default_samplerate'])

        if self.WATSON:
            authenticator = IAMAuthenticator(os.environ['IBM_API_KEY'])
            self.text_to_speech = TextToSpeechV1(
                authenticator=authenticator
            )
            self.text_to_speech.set_service_url('https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/558fb7c3-30e9-4fe7-8861-46cd1031caf9')

        else:
            self.tts = pyttsx3.init()

        self.say(f'How can I help {self.ADDRESS}?')

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
            print(status, file=sys.stderr)
        self.vosk_que.put(bytes(indata))

    
    def shutdown(self):
        print('Shutdown...')
        self.TIMER.cancel()
        sys.exit(0)

    def say(self, text):
        print(f'{self.NAME}: {text}')
        if self.SYNTHVOICE:
            if self.WATSON:
                with open('./response.wav', 'wb') as audio_file:
                    audio_file.write(
                        self.text_to_speech.synthesize(
                            text,
                            voice='en-GB_JamesV3Voice',
                            accept='audio/wav'        
                        ).get_result().content)

                audio = AudioSegment.from_wav('response.wav')
                play(audio)
            else:
                self.tts.say(text)
                self.tts.runAndWait()

    
    def listen(self):
        try:
            if self.USEVOICE:
                if not self.GOOGLE:
                    print('Listening...')
                    with sd.RawInputStream(samplerate=self.samplerate, blocksize = 8000, device=self.device, dtype='int16',
                                    channels=1, callback=self.vosk_callback):

                        rec = vosk.KaldiRecognizer(self.vosk_model, self.samplerate)
                        while True:
                            data = self.vosk_que.get()
                            if rec.AcceptWaveform(data):
                                text = json.loads(rec.Result())['text']
                                print(f'\r{text}')
                                return text
                            else:
                                text = json.loads(rec.PartialResult())['partial']
                                if text:
                                    self.stop_waiting()
                                print(f'\r{text}', end='')
                else:
                    while True:
                        print('Listening...')
                        with self.mic as source:
                            self.recog.adjust_for_ambient_noise(source)
                            audio = self.recog.listen(source)
                            try:
                                text = self.recog.recognize_google(audio)
                                print(text)
                                return text
                            except Exception as e:
                                print(e)
                                pass
            else:
                return input('You: ')
        except Exception as ex:
            print(ex)
            self.shutdown()

    
    def disengage(self):
        print('Disengaged')
        self.ENGAGED = False
        requests.get(f'{self.api_url}/reset_chat')

    def wait_for_response(self):
        if self.USEVOICE:
            self.TIMER.cancel()
            print('Waiting for response')
            self.ENGAGED = True
            self.TIMER = Timer(interval=self.TIMEOUT, function=self.disengage)
            self.TIMER.start()

    def stop_waiting(self):
        self.TIMER.cancel()

    def run(self):
        while True:
            text = self.listen()
            if text:
                text = clean_text(text)
                print('cleaned: ',text)
                if self.NAME in text or self.ENGAGED:
                    self.stop_waiting()
                    understanding = requests.get(f'{self.api_url}/understand/{text}').json()
                    response = understanding['response']
                    intent = understanding['intent']

                    if response:
                        self.say(response)
                        self.wait_for_response()
                    
                    if intent == 'shutdown':
                        self.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--hub', type=str, help='VA hub ip address', default='')
    parser.add_argument('--google', type=bool, help='Use google speech recognition', default=False)
    parser.add_argument('--watson', type=bool, help='Use watson speech synthesis', default=False)

    args = parser.parse_args()
    assistant = VirtualAssistantClient(hub_ip=args.hub, google=args.google, watson=args.watson)
    assistant.run()    