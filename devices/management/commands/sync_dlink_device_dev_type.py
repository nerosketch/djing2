from typing import Any

from django.core.management.base import BaseCommand
from devices.models import Device
from easysnmp import Session
from easysnmp.exceptions import EasySNMPError


class Command(BaseCommand):
    help = 'Scan dlink devices that available in db, and syncing data with real values on devices'

    def handle(self, *args: Any, **options: Any):
        devs = Device.objects.exclude(
            ip_address=None,
            man_passw=None,
        ).filter(dev_type__in=[1, 9, 10]).iterator()
        for dev in devs:
            try:
                print('Try to scan', str(dev))
                ses = Session(str(dev.ip_address), 2, str(dev.man_passw or 'NOT_A_PASSWORD_ACTUALLY'))
                sys_name = ses.get('.1.3.6.1.2.1.1.1.0').value
                if not sys_name or sys_name == 'NOSUCHINSTANCE':
                    continue
                if 'DGS-1100-10' in sys_name:
                    dev.dev_type = 1
                elif 'DGS-1100-06' in sys_name:
                    dev.dev_type = 10
                elif 'DGS-3120-24SC' in sys_name:
                    dev.dev_type = 9
                else:
                    continue
                print('\tSet dev type to:', sys_name)
                dev.save(update_fields=['dev_type'])
            except (EasySNMPError, SystemError) as err:
                print(str(dev), 'ERROR:', err)
