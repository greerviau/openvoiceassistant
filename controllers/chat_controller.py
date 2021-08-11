from transformers import AutoModelForCausalLM, AutoTokenizer
import openai
import torch

class ChatController(object):
    def __init__(self,
                open_ai_token = None
                ):
        self.OPENAI = True if open_ai_token else False
        openai.api_key = open_ai_token
        self.init_prompt = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How can I help you today?\n"
        self.prompt = self.init_prompt

        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-large")
        self.dialo_model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-large")
        self.bot_input_ids = None
        self.chat_history_ids = None
        self.last_chat_response = None
        self.step = 0

    def chat(self, text):
        final_response = ''
        if not self.OPENAI:
            new_user_input_ids = self.tokenizer.encode(text + self.tokenizer.eos_token, return_tensors='pt')
            bot_input_ids = torch.cat([self.chat_history_ids, new_user_input_ids], dim=-1) if self.step > 0 else new_user_input_ids
            self.chat_history_ids = self.dialo_model.generate(bot_input_ids, max_length=1000, pad_token_id=self.tokenizer.eos_token_id)
            self.step += 1
            final_response = self.tokenizer.decode(self.chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
        else:
            self.prompt += f'Human: {text}\nAI:'
            response = openai.Completion.create(
                engine="davinci",
                prompt=self.prompt,
                temperature=0.9,
                max_tokens=150,
                top_p=1,
                frequency_penalty=0.0,
                presence_penalty=0.6,
                stop=["\n", " Human:", " AI:"]
            )
            text_response = response['choices'][0]['text']
            text_response = text_response.split('Human:')[0]
            self.prompt += f'{text_response}\n'
            if len(self.prompt) > 1600:
                print('Trimming prompt')
                self.prompt = self.prompt[400:]
            final_response = text_response

        if self.last_chat_response is None:
            self.last_chat_response = final_response
        elif final_response == self.last_chat_response:
            self.reset_chat()
            return self.chat(text)
        
        return final_response

    def reset_chat(self):
        print('Chat reset')
        self.bot_input_ids = None
        self.chat_history_ids = None
        self.last_chat_response = None
        self.step = 0

        self.prompt = self.init_prompt