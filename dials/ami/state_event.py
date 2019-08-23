from json import dump
from panoramisk.message import Message

from .call import DialChannel, dial_channel_json_encoder

unk = '<unknown>'


class StateEventDispatcher(object):
    def __init__(self):
        self.calls = {}

    def unknown(self, *args, **kwargs):
        pass

    def on_new_channel(self, msg: Message):
        """
        Создаём новый канал, его первое появление,
        добавляем в self.calls новый канал по его Uniqueid.
        Если его Linkedid пустой или равен Uniqueid то для
        него ещё нет второго канала, он ещё не создан, т.е.
        на этот звонок ещё не ответили
        """
        uid = msg.Uniqueid
        if not uid:
            return
        channel = DialChannel(uid=float(uid))
        linked_id = msg.Linkedid
        if linked_id and linked_id not in (uid, unk):
            print('\t############################# PASSED linked_id:', linked_id, 'to uid', uid)
            channel.linked_id = linked_id
            channel.linked_dial_channel = self.calls.get(linked_id)

        id_num = msg.CallerIDNum
        if id_num != unk:
            channel.caller_id_num = id_num
        channel.caller_id_name = msg.CallerIDName
        self.calls[uid] = channel

    def on_moh_start(self, msg: Message):
        print(msg.Uniqueid, '------------- Moh Start -------------', end='\n' * 3)

    def on_ringing(self, msg: Message):
        print(msg.Uniqueid, '------------- Ringing -------------', end='\n'*3)

    def on_dialing(self, msg: Message):
        print(msg.Uniqueid, '------------- Dialing -------------', end='\n' * 3)

    def on_state_down(self, msg: Message):
        print(msg.Uniqueid, '------------- State Down -------------', end='\n' * 3)

    def on_state_up(self, msg: Message):
        print(msg.Uniqueid, '------------- State Up -------------', end='\n' * 3)

    def on_queue(self, msg: Message):
        print(msg.Uniqueid, '------------- Came in queue -------------', end='\n' * 3)

    def on_hangup(self, msg: Message):
        uid = msg.Uniqueid
        call_channel = self.calls.get(uid)
        if call_channel:
            call_channel.on_hangup()
            with open('./calls.%s.json' % uid, 'w') as f:
                dump(call_channel, f, ensure_ascii=False, indent=2, default=dial_channel_json_encoder)
            del self.calls[uid]
        else:
            print('Warning: dial hangup for uid "%s" not found' % uid)
        print(msg.Uniqueid, '------------- Hangup -------------', msg, end='\n' * 3)

    def on_dial_begin(self, msg: Message):
        """Звонок начат, надо соединить 2 канала, вызывающий и отвечающий"""
        # msg.Uniqueid - id вызывающего канала
        # msg.DestUniqueid - id вызываемого канала
        uid = msg.Uniqueid
        call_channel = self.calls.get(uid)
        if call_channel:
            dst_uid = msg.DestUniqueid
            if dst_uid and dst_uid != unk:
                dst_ch = self.calls.get(dst_uid)
                if dst_ch:
                    call_channel.linked_id = dst_uid
                    call_channel.linked_dial_channel = dst_ch
            print(msg.Uniqueid, '------------- Dial Begin -------------', msg, end='\n' * 3)

    def on_dial_end(self, msg: Message):
        print(msg.Uniqueid, '------------- Dial End -------------', msg, end='\n' * 3)

    def on_set_monitor_filename(self, msg: Message, val: str):
        uid = msg.Uniqueid
        call_channel = self.calls.get(uid)
        if call_channel:
            call_channel.on_set_monitor_fname(val)
        print(msg.Uniqueid, '------------- Set Monitor Fname -------------', val, end='\n' * 3)

    def on_set_queuecalls(self, msg: Message, val: str):
        print(msg.Uniqueid, '------------- Set QUEUECALLS -------------', val, end='\n' * 3)

    def on_set_queuehold_time(self, msg: Message, val: str):
        print(msg.Uniqueid, '------------- Set QUEUEHOLDTIME -------------', val, end='\n' * 3)

    def on_set_queue_talk_time(self, msg: Message, val: str):
        print(msg.Uniqueid, '------------- Set QUEUETALKTIME -------------', val, end='\n' * 3)
