#!/usr/bin/env python3
import asyncio
from panoramisk import Manager
from panoramisk.message import Message
from pprint import pprint

from ami.helps import safe_int
from ami.state_event import StateEventDispatcher

manager = Manager(
    loop=asyncio.get_event_loop(),
    host='10.12.1.2',
    username='bashmak',
    secret='partoki'
)
dispatcher = StateEventDispatcher()


@manager.register_event('*')
def callback_all_events(mngr: Manager, msg: Message):
    print('Ev', msg.Event, end=' ')
    pprint(msg)
    print('\n' * 3)


@manager.register_event('Newchannel')
def new_channel_event(mngr, msg: Message):
    print('#####NewCh', end=' ')
    pprint(msg.ChannelState)
    print('\n'*3)


@manager.register_event('Hangup')
def hangup_ev(mngr, msg):
    print('#####Hangup from', end=' ')
    pprint(msg.CallerIDNum)
    dispatcher.on_hangup(msg=msg)
    print('\n' * 3)


@manager.register_event('NewCallerid')
def new_caller_ev(mngr, msg):
    print('####New caller from', msg.CallerIDNum, msg, end='\n'*3)


@manager.register_event('Newstate')
def new_state_ev(mngr, msg):
    """
    Подняли трубку, или положили трубку, или идёт звонок
    :param mngr:
    :param msg:
    :return:
    """

    state_map = {
        3: dispatcher.on_dialing,
        5: dispatcher.on_ringing,
        6: dispatcher.on_state_up
    }
    state = safe_int(msg.ChannelState)
    print('State', state, type(state))
    if state:
        handler = state_map.get(state, dispatcher.unknown)
        r = handler(msg=msg)
        print('####New caller from', r, msg.CallerIDNum, msg, end='\n'*3)


@manager.register_event('DialBegin')
def dial_begin_ev(mngr, msg):
    """
    Звонок отвечен
    :param mngr:
    :param msg:
    :return:
    """
    print('#####Dial Begin')
    pprint(msg)
    print('\n' * 3)


@manager.register_event('DialEnd')
def dial_end_ev(mngr, msg):
    """
    Завершение звонка
    :param mngr:
    :param msg:
    :return:
    """
    print('#####Dial End')
    pprint(msg)
    print('\n' * 3)


@manager.register_event('VarSet')
def var_set_ev(mngr, msg):
    var = msg.Variable
    vars_map = {
        'MIXMONITOR_FILENAME': dispatcher.on_set_monitor_filename
    }
    print('Var', var, type(var))
    handler = vars_map.get(var, dispatcher.unknown)
    handler(msg, msg.Value)


@manager.register_event('DongleCallStateChange')
def dongle_call_state_ev(mngr, msg):
    """
    События на симке
    :param mngr:
    :param msg:
    :return:
    """
    state = msg.NewState
    states = ('released', 'active')
    if state in states:
        print('##### Dongle Call State')
        pprint(msg)


@manager.register_event('Newexten')
def new_exten_ev(mngr, msg):
    print('##### New exten')
    app = msg.Application
    cname = msg.CallerIDName
    cnum = msg.CallerIDNum
    uid = msg.Uniqueid
    pprint(msg)
    """
    Начало звонка
    :param mngr:
    :param msg:
    :return:
    """


@manager.register_event('QueueCallerJoin')
def queue_join_ev(mngr, msg):
    """
    Попал в очередь
    :param mngr:
    :param msg:
    :return:
    """


@manager.register_event('AgentCalled')
def agent_called(mngr, msg):
    """
    Начался звонок, идут гудки
    :param mngr:
    :param msg:
    :return:
    """


def main():
    manager.connect()
    try:
        manager.loop.run_forever()
    except KeyboardInterrupt:
        manager.loop.close()
        manager.close()


if __name__ == '__main__':
    main()
