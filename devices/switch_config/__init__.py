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
from .gpon import ZTE_C320, OnuZTE_F660, OnuZTE_F601
from .huawei import HuaweiS2300
from .unknown_device import UnknownDevice

DEVICE_TYPES = [
    (0, UnknownDevice),
    (1, DlinkDGS1100_10ME),
    (2, BDCOM_P3310C),
    (3, EPON_BDCOM_FORA),
    (4, EltexSwitch),
    (5, ZTE_C320),
    (6, OnuZTE_F660),
    (7, OnuZTE_F601),
    (8, HuaweiS2300),
    (9, DlinkDGS_3120_24SCSwitchInterface),
    (10, DlinkDGS_1100_06MESwitchInterface),
    (11, DlinkDGS_3627GSwitchInterface)
]

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
    'DEVICE_TYPES', 'DeviceImplementationError', 'DeviceConfigurationError',
    'DeviceConnectionError', 'BaseSNMPWorker',
    'BaseDeviceInterface', 'BasePortInterface', 'port_template',
    'ExpectValidationError', 'BasePON_ONU_Interface', 'BaseSwitchInterface',
    'BasePONInterface', 'BasePON_ONU_Interface', 'port_templates_modules',
    'Vlans', 'Macs', 'Vlan', 'MacItem', 'DeviceConsoleError'
)

# DEVICE_TYPES = (
#     (1, dev_types.DLinkDevice),
#     (2, dev_types.OLTDevice),
#     (3, dev_types.OnuDevice),
#     (4, dev_types.EltexSwitch),
#     (5, dev_types.Olt_ZTE_C320),
#     (6, dev_types.ZteOnuDevice),
#     (7, dev_types.ZteF601),
#     (8, dev_types.HuaweiSwitch),
#     (9, dev_types.ZteF660v125s)
# )
