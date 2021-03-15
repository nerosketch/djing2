from ipaddress import ip_address

from django.core.management.base import BaseCommand, CommandError, no_translations

try:
    from devices.models import Device
except ImportError:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('"networks" application depends on "devices" application. Check if it installed')

from networks.models import VlanIf


class Command(BaseCommand):
    help = "Load vlan list from specified device"

    def add_arguments(self, parser):
        parser.add_argument('ip_addr', help='device ip address', nargs=1, type=str)

    def _ok(self, text):
        self.stdout.write(self.style.SUCCESS(text))

    def _err(self, text):
        self.stdout.write(self.style.ERROR(text))

    @no_translations
    def handle(self, ip_addr: list, *args, **options):
        ip_addr = ip_addr[0]
        try:
            ip_addr = ip_address(ip_addr)
        except ValueError as err:
            raise CommandError(err)

        device = Device.objects.filter(ip_address=str(ip_addr)).first()
        if device is None:
            raise CommandError('Device not found')

        vlans = device.dev_get_all_vlan_list()
        for vlan in vlans:
            if not vlan.title:
                self._err("Skipping vlan with vid=%d. Empty title" % vlan.vid)
                continue

            db_vlan_exists = VlanIf.objects.filter(vid=vlan.vid).exists()
            if db_vlan_exists:
                self._err(f"Skip: {vlan.vid}\t\talready exists, continue")
            else:
                VlanIf.objects.create(
                    vid=vlan.vid,
                    title=vlan.title.decode() if isinstance(vlan.title, bytes) else vlan.title,
                    is_management=bool(vlan.is_management)
                )
                self._ok(f"OK: {vlan.vid}\t\t{vlan.title} created")
