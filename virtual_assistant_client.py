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
from utils import clean_text
import scapy.all as scapy
import argparse
import wave
import base64

class VirtualAssistantClient(threading.Thread):
    
    def __init__(self, hub_ip, use_voice, synth_voice, google, mic_tag, blocksize, samplerate, debug, rpi):
        self.USEVOICE = use_voice
        self.SYNTHVOICE = synth_voice
        self.GOOGLE = google
        self.BLOCKSIZE = blocksize
        self.SAMPLERATE = samplerate
        self.DEBUG = debug
        self.RPI = rpi

        port = 8000
        if not hub_ip:
            host = self.scan_for_hub(port)
        else:
            host = hub_ip

        self.log(f'\nFound VA HUB | ip: {host}')

        self.api_url = f'http://{host}:{port}'
        name_and_address = requests.get(f'{self.api_url}/get_hub_details').json()
        self.NAME = name_and_address['name']
        self.ADDRESS = name_and_address['address']

        devices = sr.Microphone.list_microphone_names()
        self.log(devices)
        if not mic_tag:
            mic_tag='microphone'
        output = [idx for idx, element in enumerate(devices) if mic_tag in element.lower()]
        self.device = output[0]
        self.log(f'Device {devices[self.device]} index {self.device}')
        #self.mic = sr.Microphone(device_index = self.device)

        device_info = sd.query_devices(self.device, 'input')
        if self.SAMPLERATE is None:
            self.SAMPLERATE = int(device_info['default_samplerate'])

        self.ENGAGED = True
        self.HOT = False
        self.TIMEOUT = 15.0
        self.TIMER = Timer(interval=30.0, function=self.disengage)
        if self.USEVOICE:
            self.TIMER.start()

        self.record_queue = queue.Queue()
        
        self.log(f'Debug Mode: {self.DEBUG}')
        self.log(f'Use Voice Input: {self.USEVOICE}')
        self.log(f'Using GOOGLE: {self.GOOGLE}')
        self.log(f'Synth Voice Output: {self.USEVOICE}')
        self.log(f'RPI: {self.RPI}')
        self.log(f'Samplerate: {self.SAMPLERATE}')
        self.log(f'Blocksize: {self.BLOCKSIZE}')

        self.synth_and_say(f'How can I help {self.ADDRESS}?')
        
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

    def scan_for_hub(self, port):
        devices = self.scan('10.0.0.1/24')
        self.log(devices)
        self.log('Looking for VA HUB...')
        for device in devices:
            ip = device['ip']
            self.log(f'\rTesting: {ip}', end='')
            try:
                response = requests.get(f'http://{ip}:{port}/is_va_hub').json()
                return ip
            except:
                pass

    def log(self, log_text, end='\n'):
        if self.DEBUG:
            print(log_text, end=end)
    
    def shutdown(self):
        print('Shutdown...')
        self.TIMER.cancel()
        sys.exit(0)

    def synth_and_say(self, text):
        print(f'{self.NAME}: {text}')
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

    def save_audio(self, audio):
        with open('client_command.wav', 'wb') as f:
            f.write(audio.get_wav_data())
                
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
                        print(e)
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
                print(status, file=sys.stderr)
            self.record_queue.put(indata.copy())

        while True:
            self.vosk_queue = queue.Queue()
            self.record_queue = queue.Queue()
            with sf.SoundFile('./client_command.wav', mode='w', samplerate=self.SAMPLERATE, subtype='PCM_16', channels=1) as outFile:
                with sd.InputStream(samplerate=self.SAMPLERATE, blocksize = 8000, device=self.device, dtype='int16',
                                        channels=1, callback=input_stream_callback):

                    #print('Listening...')

                    rec = vosk.KaldiRecognizer(vosk_model, self.SAMPLERATE)
                    audio_cache = []
                    while True:
                        data = self.record_queue.get()
                        if rec.AcceptWaveform(bytes(data)):
                            outFile.write(data)
                            text = json.loads(rec.Result())['text']
                            self.log(text)
                            break
                        else:
                            partial = json.loads(rec.PartialResult())['partial']
                            if partial:
                                for i in range(len(audio_cache)):
                                    outFile.write(audio_cache.pop(0))
                                audio_cache = []
                                outFile.write(data)
                            else:
                                audio_cache.append(data)
                                if len(audio_cache) > 5:
                                    audio_cache.pop(0)
            self.understand_from_audio_and_synth(open('client_command.wav', 'rb'))
            

    def understand_from_audio_and_synth(self, audio):
        files = {'audio_file': audio}
        response = requests.post(
            f'{self.api_url}/understand_from_audio_and_synth',
            files=files
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
            print(f'{self.NAME}: {response}')
            self.synth_and_say(response)
            self.wait_for_response()
        
        if intent == 'shutdown':
            self.shutdown()

    def process_understanding_and_say(self, understanding):
        self.stop_waiting()
        response = understanding['response']
        intent = understanding['intent']
        conf = understanding['conf']
        synth = base64.b64decode(understanding['synth'])
        self.log(f'intent: {intent} - conf: {conf} - resp: {response}')
        if response:
            print(f'{self.NAME}: {response}')
            if self.SYNTHVOICE:
                with open('./client_response.wav', 'wb') as audio_file:
                    audio_file.write(synth)
            self.say()
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
                if self.GOOGLE:
                    self.listen_with_google()
                else:
                    self.listen_with_hotword()
            else:
                while True:
                    text = input('You: ')
                    self.understand_from_text_and_synth(text)

        except Exception as ex:
                self.log(ex)
                self.shutdown()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--hub', type=str, help='VA hub ip address', default='')
    parser.add_argument('--useVoice', help='Use voice as input', action='store_true')
    parser.add_argument('--synthVoice', help='Synthesize voice as output', action='store_true')
    parser.add_argument('--google', help='Use google speech recognition', action='store_true')
    parser.add_argument('--mic', type=str, help='Microphone tag', default='')
    parser.add_argument('--blocksize', type=int, help='Blocksize for voice capture', default=8000)
    parser.add_argument('--samplerate', type=int, help='Samplerate for microphone', default=None)
    parser.add_argument('--debug', help='Synthesize voice as output', action='store_true')
    parser.add_argument('--rpi', help='Running on raspberry pi', action='store_true')

    args = parser.parse_args()
    assistant = VirtualAssistantClient(*vars(args).values())
    assistant.run()
