import argparse
import os
import queue
import sounddevice as sd
import vosk
import sys
import json
import webrtcvad
import numpy as np
import speech_recognition as sr 
import requests
import wave
import io

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    '-f', '--filename', type=str, metavar='FILENAME',
    help='audio file to store recording to')
parser.add_argument(
    '-m', '--model', type=str, metavar='MODEL_PATH',
    help='Path to the model')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-r', '--samplerate', type=int, help='sampling rate')
args = parser.parse_args(remaining)

if args.model is None:
    args.model = "model"
if not os.path.exists(args.model):
    print ("Please download a model for your language from https://alphacephei.com/vosk/models")
    print ("and unpack as 'model' in the current folder.")
    parser.exit(0)
if args.samplerate is None:
    device_info = sd.query_devices(args.device, 'input')
    # soundfile expects an int, sounddevice provides a float:
    args.samplerate = int(device_info['default_samplerate'])

q = queue.Queue()
block_size = 8000
hotword = 'david'

#vad = webrtcvad.Vad()

recog = sr.Recognizer()
print(sr.Microphone.list_microphone_names())
mic = sr.Microphone(device_index = args.device)

model = vosk.Model(args.model)

with mic as source:
    recog.adjust_for_ambient_noise(source)
    try:
        while True:
            audio = recog.listen(source)
            print('Done Listening')
            with open('command.wav', 'wb') as f:
                f.write(audio.get_wav_data())
            wave_reader = wave.open('command.wav', 'rb')
            rec = vosk.KaldiRecognizer(model, wave_reader.getframerate(), f'["{hotword}", "[unk]"]')
            final = []
            while True:
                data = wave_reader.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    rec.Result()
                else:
                    partial = json.loads(rec.PartialResult())['partial']
                    final = list(set().union(partial.split(), final))
            print('Final')
            print(final)
            print('Done')       

    except KeyboardInterrupt:
        print('\nDone')
        parser.exit(0)
    except Exception as e:
        parser.exit(type(e).__name__ + ': ' + str(e))