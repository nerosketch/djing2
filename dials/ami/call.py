from typing import Tuple


class Uid(object):
    _uid: Tuple[int, int] = (0, 0)

    def __init__(self, uid):
        if isinstance(uid, float):
            suid = str(uid)
            nuid = suid.split('.')
            self._uid = int(nuid[0]), int(nuid[1])
        elif isinstance(uid, str):
            nuid = uid.split('.')
            self._uid = int(nuid[0]), int(nuid[1])
        elif isinstance(uid, Tuple):
            self._uid = int(uid[0]), int(uid[1])

    def __float__(self):
        return float('%d.%d' % self._uid)

    def __str__(self):
        return '%d.%d' % self._uid

    def __eq__(self, other):
        return self._uid == other._uid


class DialChannel(object):
    """
    Вызов с одной стороны звонка. При входящем звонке
    абонент и оператор оказываются в разных DialChannel,
    соединённых уникальным идентификатором <Uid>
    """
    _uid: Uid = None
    _linked_id: Uid = None
    linked_dial_channel = None
    caller_id_num = None
    caller_id_name = None
    fname = None

    def __init__(self, uid: float):
        self.uid = uid

    def _uid_get(self):
        return self._uid

    def _uid_set(self, uid):
        self._uid = Uid(uid)

    def _linked_id_get(self):
        return self._linked_id

    def _linked_id_set(self, uid):
        self._linked_id = Uid(uid)

    uid = property(_uid_get, _uid_set)
    linked_id = property(_linked_id_get, _linked_id_set)

    def on_hangup(self):
        """Срабатывает когда в этом канале положили трубку.
           После этого канал удаляется"""
        pass
        # print('###################### DialChannel hangup', self.uid)

    def on_set_monitor_fname(self, fname):
        self.fname = fname or None
        pass
        # print('###################### DialChannel monitor fname', fname)

    def __str__(self):
        return 'Channel <%s>' % self.uid

    def __del__(self):
        if self.linked_dial_channel is not None:
            del self.linked_dial_channel


def dial_channel_json_encoder(channel: DialChannel):
    if isinstance(channel, DialChannel):
        r = {
            'uid': str(channel.uid),
            'linked_id': str(channel.linked_id) if channel.linked_id else None,
            'caller_id_num': channel.caller_id_num or None,
            'caller_id_name': channel.caller_id_name or None,
            'fname': channel.fname or None
        }
        print('linked_dial_channel', channel.linked_dial_channel)
        if channel.linked_dial_channel:
            r['linked_dial_channel'] = {
                'uid': str(channel.linked_dial_channel.uid),
                'linked_id': str(channel.linked_dial_channel.linked_id),
                'caller_id_num': channel.linked_dial_channel.caller_id_num,
                'caller_id_name': channel.linked_dial_channel.caller_id_name,
                'fname': channel.linked_dial_channel.fname,
            }
        return r
    raise TypeError(repr(channel) + " is not JSON serializable")
