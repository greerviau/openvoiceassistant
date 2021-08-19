from typing import Optional
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import uvicorn
import pyttsx3
from virtual_assistant import VirtualAssistant
import wave

app = FastAPI()

VA = VirtualAssistant(name='jasper', address='sir', debug=False)

host = '0.0.0.0'
port = 8000
tts = pyttsx3.init()
tts.setProperty('voice', 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_enGB_GeorgeM')
tts.setProperty('rate',175)

@app.get('/is_va_hub')
def is_va_hub():
    return {
        'ip':host,
        'port':port
    }

@app.get('/predict_intent/{text}')
def predict_intent(text: str):
    intent, conf = VA.predict_intent(text)
    return {
        'intent':intent,
        'conf':conf
    }

@app.get('/understand/{text}')
def understand(text: str):
    response, intent, conf = VA.understand(text)
    return {
        'response':response,
        'intent':intent,
        'conf':conf
    }

@app.get('/synth_voice/{text}')
def synth_voice(text: str):
    tts.save_to_file(text, 'synth_response.wav')
    tts.runAndWait()
    with open('synth_response.wav', 'rb') as fd:
        contents = fd.read()
        return Response(content = contents)
        

@app.get('/get_name_and_address')
def get_name_and_address():
    name = VA.get_name()
    address = VA.get_address()

    return {
        'name':name,
        'address':address
    }

@app.get('/reset_chat', status_code=201)
def reset_chat():
    VA.reset_chat()

if __name__ == '__main__':
    uvicorn.run(app, host=host, port=port)