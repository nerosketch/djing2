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
    _uid: Uid
    _linked_id: Uid
    linked_dial_channel = None
    caller_id_num = ''
    caller_id_name = ''
    fname = ''

    def __init__(self, uid: float):
        self.uid = uid

    def _uid_get(self):
        return self._uid

    def _uid_set(self, uid):
        self._uid = Uid(uid)

    def _linked_id_get(self):
        return self._uid

    def _linked_id__set(self, uid):
        self._uid = Uid(uid)

    uid = property(_uid_get, _uid_set)
    linked_id = property(_linked_id_get, _linked_id__set)

    def on_hangup(self):
        """Срабатывает когда в этом канале положили трубку"""
        print('###################### DialChannel hangup', self.uid)

    def on_set_monitor_fname(self, fname):
        self.fname = fname
        print('###################### DialChannel monitor fname', fname)

    def json(self):
        return {
            'uid': float(self.uid),
            'linked_id': float(self.linked_id),
            'caller_id_num': self.caller_id_num,
            'caller_id_name': self.caller_id_name,
            'fname': self.fname
        }

    def __str__(self):
        return self.uid

    def __del__(self):
        if self.linked_dial_channel is not None:
            del self.linked_dial_channel
