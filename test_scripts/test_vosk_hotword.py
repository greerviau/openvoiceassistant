from vosk import Model, KaldiRecognizer
import sys
import os
import wave

if not os.path.exists("../vosk"):
    print ("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current folder.")
    exit (1)

wf = wave.open(sys.argv[1], "rb")
if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
    print ("Audio file must be WAV format mono PCM.")
    exit (1)

model = Model("../vosk")

# You can also specify the possible word or phrase list as JSON list, the order doesn't have to be strict
rec = KaldiRecognizer(model, wf.getframerate(), '[ "keyword", "[unk]" ]')

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        print(rec.Result())
    else:
        print(rec.PartialResult())

print(rec.FinalResult())