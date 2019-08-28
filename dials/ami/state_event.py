from datetime import datetime
from json import dump
from panoramisk.message import Message

from .helps import safe_float
from .call import DialChannel, dial_channel_json_encoder


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
        uid = safe_float(msg.Uniqueid)
        if not uid:
            return
        channel = DialChannel(uid=uid)
        channel.create_time = datetime.now()
        linked_id = safe_float(msg.Linkedid)
        if linked_id and linked_id != uid:
            channel.linked_id = linked_id
            channel.linked_dial_channel = self.calls.get(linked_id)

        id_num = msg.CallerIDNum
        if id_num != '<unknown>':
            channel.caller_id_num = id_num
        channel.caller_id_name = msg.CallerIDName

        # Channel 'Dongle/sim_8318999-010000088d' || 'PJSIP/312-00001a7d
        dev_name = msg.Channel.split('-')
        if len(dev_name) > 0:
            channel.dev_name = dev_name[0]

        self.calls[uid] = channel

    # def on_moh_start(self, msg: Message):
        # print(msg.Uniqueid, '------------- Moh Start -------------', end='\n' * 3)

    # def on_ringing(self, msg: Message):
        # print(msg.Uniqueid, '------------- Ringing -------------', end='\n'*3)

    # def on_dialing(self, msg: Message):
        # print(msg.Uniqueid, '------------- Dialing -------------', end='\n' * 3)

    # def on_state_down(self, msg: Message):
        # print(msg.Uniqueid, '------------- State Down -------------', end='\n' * 3)

    # def on_state_up(self, msg: Message):
        # print(msg.Uniqueid, '------------- State Up -------------', end='\n' * 3)

    # def on_queue(self, msg: Message):
        # print(msg.Uniqueid, '------------- Came in queue -------------', end='\n' * 3)

    def on_hangup(self, msg: Message):
        uid = safe_float(msg.Uniqueid)
        call_channel = self.calls.get(uid)
        if call_channel:
            call_channel.end_time = datetime.now()
            call_channel.on_hangup()
            with open('./calls.%f.json' % uid, 'w') as f:
                dump(call_channel, f, ensure_ascii=False, indent=2, default=dial_channel_json_encoder)
            del self.calls[uid]
            # print('Warning: dial hangup for uid "%f" not found' % uid)
        # print(msg.Uniqueid, '------------- Hangup -------------', end='\n' * 3)

    def on_dial_begin(self, msg: Message):
        """Звонок начат, надо соединить 2 канала, вызывающий и отвечающий"""
        # msg.Uniqueid - id вызывающего канала
        # msg.DestUniqueid - id вызываемого канала
        uid = safe_float(msg.Uniqueid)
        call_channel = self.calls.get(uid)
        if call_channel:
            dst_uid = safe_float(msg.DestUniqueid)
            if dst_uid:
                dst_ch = self.calls.get(dst_uid)
                if dst_ch:
                    call_channel.linked_id = dst_uid
                    call_channel.linked_dial_channel = dst_ch
            # print(msg.Uniqueid, '------------- Dial Begin -------------', end='\n' * 3)

    # def on_dial_end(self, msg: Message):
        # print(msg.Uniqueid, '------------- Dial End -------------', end='\n' * 3)

    def on_set_monitor_filename(self, msg: Message, val: str):
        uid = safe_float(msg.Uniqueid)
        call_channel = self.calls.get(uid)
        if call_channel:
            call_channel.on_set_monitor_fname(val)
        # print(msg.Uniqueid, '------------- Set Monitor Fname -------------', val, end='\n' * 3)

    # def on_set_queuecalls(self, msg: Message, val: str):
        # print(msg.Uniqueid, '------------- Set QUEUECALLS -------------', val, end='\n' * 3)

    # def on_set_queuehold_time(self, msg: Message, val: str):
    #     print(msg.Uniqueid, '------------- Set QUEUEHOLDTIME -------------', val, end='\n' * 3)

    # def on_set_queue_talk_time(self, msg: Message, val: str):
    #     print(msg.Uniqueid, '------------- Set QUEUETALKTIME -------------', val, end='\n' * 3)

    def on_agent_complete(self, msg: Message, talk_time: int, hold_time: int):
        uid = safe_float(msg.Uniqueid)
        call_channel = self.calls.get(uid)
        if call_channel:
            call_channel.hold_time = hold_time
            call_channel.talk_time = talk_time
            call_channel.on_agent_complete(
                msg=msg,
                talk_time=talk_time,
                hold_time=hold_time
            )
        # print(msg.Uniqueid, '------------- AgentComplete -------------', talk_time, hold_time, end='\n' * 3)
