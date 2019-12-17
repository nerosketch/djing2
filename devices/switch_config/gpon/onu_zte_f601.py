from typing import Dict

from .onu_zte_f660 import OnuZTE_F660
from .zte_utils import reg_dev_zte
from .f601_expect import register_onu


class OnuZTE_F601(OnuZTE_F660):
    description = 'Zte ONU F601'

    def register_device(self, extra_data: Dict):
        return reg_dev_zte(self.db_instance, extra_data, register_onu)
