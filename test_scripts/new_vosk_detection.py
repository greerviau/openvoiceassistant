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

vosk_queue= queue.Queue()
record_queue = queue.Queue()

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
    vosk_queue.put(bytes(indata))
    record_queue.put(indata.copy())

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)

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
                    data = vosk_queue.get()
                    outFile.write(record_queue.get())
                    if rec.AcceptWaveform(data):
                        text = json.loads(rec.Result())['text']
                        print('Final ',text)
                        if 'hello' in text:
                            hotword = True
                    else:
                        print(rec.PartialResult())

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