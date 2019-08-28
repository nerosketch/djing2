from panoramisk.message import Message
from .helps import safe_float


class DialChannel(object):
    """
    Вызов с одной стороны звонка. При входящем звонке
    абонент и оператор оказываются в разных DialChannel,
    соединённых уникальным идентификатором
    """
    _uid: float = None
    _linked_id: float = None
    linked_dial_channel = None
    caller_id_num = None
    caller_id_name = None
    fname = None
    hold_time = 0
    talk_time = 0
    create_time = 0
    end_time = 0
    dev_name = ''

    def __init__(self, uid: float):
        self.uid = uid

    def _uid_get(self):
        return self._uid

    def _uid_set(self, uid: float):
        self._uid = safe_float(uid)

    def _linked_id_get(self):
        return self._linked_id

    def _linked_id_set(self, uid: float):
        self._linked_id = safe_float(uid)

    uid = property(_uid_get, _uid_set)
    linked_id = property(_linked_id_get, _linked_id_set)

    def on_hangup(self):
        """Срабатывает когда в этом канале положили трубку.
           После этого канал удаляется"""
        pass
        # print('###################### DialChannel hangup', self.uid)

    def on_set_monitor_fname(self, fname: str):
        self.fname = fname or None
        # print('###################### DialChannel monitor fname', fname)

    def on_agent_complete(self, msg: Message, talk_time: int, hold_time: int):
        print('###################### Agent complete', self.uid)

    def __str__(self):
        return 'Channel <%s>' % self.uid

    def __del__(self):
        if self.linked_dial_channel is not None:
            del self.linked_dial_channel


def dial_channel_json_encoder(channel: DialChannel):
    if isinstance(channel, DialChannel):
        r = {
            'uid': channel.uid,
            'linked_id': channel.linked_id or None,
            'caller_id_num': channel.caller_id_num or None,
            'caller_id_name': channel.caller_id_name or None,
            'fname': channel.fname or None,
            'hold_time': channel.hold_time,
            'talk_time': channel.talk_time,
            'create_time': str(channel.create_time),
            'end_time': str(channel.end_time),
            'dev_name': channel.dev_name
        }
        print('linked_dial_channel', channel.linked_dial_channel)
        if channel.linked_dial_channel:
            r['linked_dial_channel'] = {
                'uid': channel.linked_dial_channel.uid,
                'linked_id': channel.linked_dial_channel.linked_id,
                'caller_id_num': channel.linked_dial_channel.caller_id_num,
                'caller_id_name': channel.linked_dial_channel.caller_id_name,
                'fname': channel.linked_dial_channel.fname,
                'hold_time': channel.linked_dial_channel.hold_time,
                'talk_time': channel.linked_dial_channel.talk_time,
                'create_time': str(channel.linked_dial_channel.create_time),
                'end_time': str(channel.linked_dial_channel.end_time),
                'dev_name': channel.linked_dial_channel.dev_name
            }
        return r
    raise TypeError(repr(channel) + " is not JSON serializable")
