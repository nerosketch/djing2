from panoramisk.message import Message


class StateEventDispatcher(object):
    def __init__(self):
        pass

    def unknown(self, *args, **kwargs):
        pass

    def on_ringing(self, msg: Message):
        print('------------- Ringing -------------', end='\n'*3)

    def on_dialing(self, msg: Message):
        print('------------- Dialing -------------', end='\n' * 3)

    def on_state_up(self, msg: Message):
        print('------------- State Up -------------', end='\n' * 3)

    def on_hangup(self, msg: Message):
        print('------------- Hangup -------------', end='\n' * 3)

    def on_set_monitor_filename(self, msg: Message, val: str):
        print('------------- Set Monitor Fname -------------', val, end='\n' * 3)
