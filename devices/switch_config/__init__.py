import importlib
import os
from .base import *
from .dlink import (
    DlinkDGS1100_10ME, DlinkDGS_3120_24SCSwitchInterface,
    DlinkDGS_1100_06MESwitchInterface, DlinkDGS_3627GSwitchInterface
)
from .eltex import EltexSwitch
from .epon import BDCOM_P3310C, EPON_BDCOM_FORA
from .expect_util import *
from .gpon import ZTE_C320, OnuZTE_F660, OnuZTE_F601, OnuZTE_F660_Bridge
from .huawei import HuaweiS2300
from .unknown_device import UnknownDevice


DEVICE_TYPE_UNKNOWN = 0
DEVICE_TYPE_DlinkDGS1100_10ME = 1
DEVICE_TYPE_BDCOM_P3310C = 2
DEVICE_TYPE_EPON_BDCOM_FORA = 3
DEVICE_TYPE_EltexSwitch = 4
DEVICE_TYPE_ZTE_C320 = 5
DEVICE_TYPE_OnuZTE_F660 = 6
DEVICE_TYPE_OnuZTE_F601 = 7
DEVICE_TYPE_HuaweiS2300 = 8
DEVICE_TYPE_DlinkDGS_3120_24SCSwitchInterface = 9
DEVICE_TYPE_DlinkDGS_1100_06MESwitchInterface = 10
DEVICE_TYPE_DlinkDGS_3627GSwitchInterface = 11
DEVICE_TYPE_OnuZTE_F660_BRIDGE = 12

DEVICE_TYPES = [
    (DEVICE_TYPE_UNKNOWN, UnknownDevice),
    (DEVICE_TYPE_DlinkDGS1100_10ME, DlinkDGS1100_10ME),
    (DEVICE_TYPE_BDCOM_P3310C, BDCOM_P3310C),
    (DEVICE_TYPE_EPON_BDCOM_FORA, EPON_BDCOM_FORA),
    (DEVICE_TYPE_EltexSwitch, EltexSwitch),
    (DEVICE_TYPE_ZTE_C320, ZTE_C320),
    (DEVICE_TYPE_OnuZTE_F660, OnuZTE_F660),
    (DEVICE_TYPE_OnuZTE_F601, OnuZTE_F601),
    (DEVICE_TYPE_HuaweiS2300, HuaweiS2300),
    (DEVICE_TYPE_DlinkDGS_3120_24SCSwitchInterface, DlinkDGS_3120_24SCSwitchInterface),
    (DEVICE_TYPE_DlinkDGS_1100_06MESwitchInterface, DlinkDGS_1100_06MESwitchInterface),
    (DEVICE_TYPE_DlinkDGS_3627GSwitchInterface, DlinkDGS_3627GSwitchInterface),
    (DEVICE_TYPE_OnuZTE_F660_BRIDGE, OnuZTE_F660_Bridge)
]

DEVICE_ONU_TYPES = (
    DEVICE_TYPE_EPON_BDCOM_FORA,
    DEVICE_TYPE_OnuZTE_F660,
    DEVICE_TYPE_OnuZTE_F601
)

port_templates_modules = {}
#
# Import port template modules from 'port_templates' subdirectory of each
# switch config module
#
base_dir = os.path.dirname(os.path.abspath(__file__))
all_directories = filter(lambda fl: not fl.startswith('_') and os.path.isdir(
    os.path.join(base_dir, fl)
), os.listdir(path=base_dir))
func_num = 0
for dirc in all_directories:
    try:
        port_template_module_files = filter(lambda fl: not fl.startswith('_'), os.listdir(
            path=os.path.join(base_dir, dirc, 'port_templates')
        ))
        for port_template_module_file in port_template_module_files:
            port_template_module_file = port_template_module_file.split('.')[0]
            port_template_mod = importlib.import_module(
                'devices.switch_config.%s.port_templates.%s' % (dirc, port_template_module_file))
            func_names = filter(lambda fn: not fn.startswith('_'), dir(port_template_mod))
            for func_name in func_names:
                func = getattr(port_template_mod, func_name)
                if hasattr(func, 'is_port_template') and func.is_port_template:
                    port_templates_modules[func_num] = func
                    func_num += 1
    except (ModuleNotFoundError, FileNotFoundError):
        continue

__all__ = (
    'DEVICE_TYPES', 'DEVICE_TYPE_UNKNOWN', 'DEVICE_TYPE_DlinkDGS1100_10ME',
    'DEVICE_TYPE_BDCOM_P3310C', 'DEVICE_TYPE_EPON_BDCOM_FORA', 'DEVICE_TYPE_EltexSwitch',
    'DEVICE_TYPE_ZTE_C320', 'DEVICE_TYPE_OnuZTE_F660', 'DEVICE_TYPE_OnuZTE_F601',
    'DEVICE_TYPE_HuaweiS2300', 'DEVICE_TYPE_DlinkDGS_3120_24SCSwitchInterface',
    'DEVICE_TYPE_DlinkDGS_1100_06MESwitchInterface', 'DEVICE_TYPE_DlinkDGS_3627GSwitchInterface',
    'DEVICE_ONU_TYPES',
    'DeviceImplementationError', 'DeviceConfigurationError',
    'DeviceConnectionError', 'BaseSNMPWorker',
    'BaseDeviceInterface', 'BasePortInterface', 'port_template',
    'ExpectValidationError', 'BasePON_ONU_Interface', 'BaseSwitchInterface',
    'BasePONInterface', 'BasePON_ONU_Interface', 'port_templates_modules',
    'Vlans', 'Macs', 'Vlan', 'MacItem', 'DeviceConsoleError'
)
