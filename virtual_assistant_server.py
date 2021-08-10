from typing import Optional
from fastapi import FastAPI
import uvicorn
from virtual_assistant import VirtualAssistant

app = FastAPI()

VA = VirtualAssistant()

host = '0.0.0.0'
port = 8000

@app.route('/is_va_hub', methods=['GET'])
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