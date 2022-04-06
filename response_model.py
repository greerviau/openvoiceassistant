class Action(object):
    def __init__(self, method, data):
        self.method = method
        self.data = data

class Response(object):
    response_text = None
    action = None
    callback = ''
    def __init__(self, response_text: str, action: Action = '', callback: str = ''):
        self.response_text = response_text
        self.action = action
        self.callback = callback

    def __str__(self):
        return f'response {self.response_text} - action {self.action} - callback {self.callback}'