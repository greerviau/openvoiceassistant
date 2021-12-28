class Action(object):
    def __init__(self, method, data):
        self.method = method
        self.data = data

class Response(object):
    response = None
    action = None
    callback = ''
    def __init__(self, response: str, action: Action = '', callback: str = ''):
        self.response = response
        self.action = action
        self.callback = callback

    def to_string(self):
        return {'response': self.response, 'action': self.action, 'callback': self.callback}