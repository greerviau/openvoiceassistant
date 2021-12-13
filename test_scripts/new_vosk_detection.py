import argparse
import os
import queue
import sounddevice as sd
import soundfile as sf
import vosk
import sys
import threading
import time
import json

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)

queue= queue.Queue()

running = False
hotword = False

model = '../vosk_small'
filename = 'test.wav'
device = 3

device_info = sd.query_devices(device, 'input')
# soundfile expects an int, sounddevice provides a float:
samplerate = int(device_info['default_samplerate'])

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    queue.put(indata.copy())

model = vosk.Model(model)

def rec():
    global hotword
    global running
    print('Recording')
    while running:
        with sf.SoundFile(filename, mode='w', samplerate=samplerate, subtype='PCM_16', channels=1) as outFile:
            with sd.InputStream(samplerate=samplerate, blocksize = 8000, device=device, dtype='int16',
                                    channels=1, callback=callback):
                print('#' * 80)
                print('Press Ctrl+C to stop the recording')
                print('#' * 80)

                rec = vosk.KaldiRecognizer(model, samplerate)
                while not hotword and running:
                    data = queue.get()
                    if rec.AcceptWaveform(bytes(data)):
                        outFile.write(data)
                        text = json.loads(rec.Result())['text']
                        print('\nFinal ',text)
                        if 'david' in text:
                            hotword = True
                    else:
                        partial = json.loads(rec.PartialResult())['partial']
                        print(f'\r{partial}', end='')
                        if partial:
                            #print('Writing to file')
                            for i in range(len(audio_cache)):
                                outFile.write(audio_cache.pop(0))
                            audio_cache = []
                            outFile.write(data)
                        else:
                            audio_cache.append(data)
                            if len(audio_cache) > 5:
                                audio_cache.pop(0)

                print('Process recording')
                hotword = False
    print('Exiting')
        
recorder = threading.Thread(target=rec)

def start():
    global running
    running = True
    recorder.start()

def stop():
    global running
    running = False
    recorder.join()

print('Starting')
start()

try:
    while True:
        time.sleep(1)
except:
    stop()