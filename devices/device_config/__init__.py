import importlib
import os
from devices.device_config.pon import *
from devices.device_config.switch import *
from .base import *
from .expect_util import ExpectValidationError
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
]

DEVICE_ONU_TYPES = [
    DEVICE_TYPE_EPON_BDCOM_FORA,
    DEVICE_TYPE_OnuZTE_F660,
    DEVICE_TYPE_OnuZTE_F601
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
                'devices.device_config.%s.port_templates.%s' % (dirc, port_template_module_file))
            func_names = filter(lambda fn: not fn.startswith('_'), dir(port_template_mod))
            for func_name in func_names:
                func = getattr(port_template_mod, func_name)
                if hasattr(func, 'is_port_template') and func.is_port_template:
                    port_templates_modules[func_num] = func
                    func_num += 1
    except (ModuleNotFoundError, FileNotFoundError):
        continue


# Check type for device config classes
def _check_device_config_types():
    allowed_symbols_pattern = re.compile(r'^\w{1,64}$')
    all_dtypes = (klass.get_config_types() for code, klass in DEVICE_TYPES if
                  issubclass(klass, (BasePON_ONU_Interface, BasePortInterface)))
    all_dtypes = (a for b in all_dtypes if b for a in b)
    for dtype in all_dtypes:
        if not issubclass(dtype, DeviceConfigType):
            raise DeviceImplementationError(
                'device config type "%s" must be subclass of DeviceConfigType' % repr(dtype))
        device_config_short_code = str(dtype.short_code)
        if not allowed_symbols_pattern.match(device_config_short_code):
            raise DeviceImplementationError(
                'device config "%s" short_code must be equal regexp "^\w{1,64}$"' % repr(dtype))


_check_device_config_types()
