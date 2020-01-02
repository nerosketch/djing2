from .base import *
from .expect_util import *
from .unknown_device import UnknownDevice
from .dlink import DlinkDGS1100_10ME
from .epon import BDCOM_P3310C, EPON_BDCOM_FORA
from .gpon import ZTE_C320, OnuZTE_F660, OnuZTE_F601
from .eltex import EltexSwitch
from .huawei import HuaweiS2300


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
]

__all__ = (
    'DEVICE_TYPES', 'DeviceImplementationError', 'DeviceConfigurationError',
    'SNMPBaseWorker', 'DevBase',
    'ExpectValidationError', 'MySpawn',
    'BaseTelnet', 'BaseTelnetSwitch', 'BaseTelnetPON', 'BasePort',
    'DeviceConsoleError', 'Vlans', 'Macs'
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
