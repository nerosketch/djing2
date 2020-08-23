from typing import Dict

from .f660_expect_bridge import register_onu
from .onu_zte_f660 import OnuZTE_F660
from .zte_utils import reg_dev_zte


class OnuZTE_F660_Bridge(OnuZTE_F660):
    description = 'Zte ONU F660 Bridge'

    def register_device(self, extra_data: Dict):
        # TODO: It may be deprecated
        return reg_dev_zte(self.dev_instance, extra_data, register_onu)
