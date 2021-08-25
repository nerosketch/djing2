from datetime import datetime
from django.core.management.base import CommandError
from ._base_file_based_cmd import BaseFileBasedCommand
from sorm_export.models import datetime_format
from sorm_export.hier_export.gateways import store_fname
from sorm_export.serializers.gateways import GatewayTypeExportChoices, GatewayExportFormatSerializer
from sorm_export.hier_export.base import simple_export_decorator


@simple_export_decorator
def _make_gateways_data(gw_type: str, descr: str, gw_addr: str, start_usage_time: datetime, gw_ip_addrs: str,
                        event_time: datetime):

    dat = [{
        'gw_id': 0,
        'gw_type': gw_type,
        'descr': descr,
        'gw_addr': gw_addr,
        'start_use_time': start_usage_time,
        # 'deactivate_time':
        'ip_addrs': gw_ip_addrs
    }]
    ser = GatewayExportFormatSerializer(data=dat, many=True)
    return ser, store_fname



class Command(BaseFileBasedCommand):
    help = ("Creates or replace gateways: "
            "https://wiki.vasexperts.ru/doku.php"
            "?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_gateways:start")

    store_fname = store_fname

    def add_arguments(self, parser):
        parser.add_argument(
            '--add', action='store_true', help="Add new gateway"
        )
        parser.add_argument(
            '--show', action='store_true', help="List available gateways"
        )
        parser.add_argument(
            '--rm', action='store_true', help="Remove special gateways by id"
        )

    def add(self, val):
        gw_types = [k for k, v in GatewayTypeExportChoices.choices]
        gw_type = input("Gateway type %s: " % gw_types)
        if gw_type not in gw_types:
            raise CommandError('Bad gateway type, select from %s' % gw_types)

        descr = input('Description: ')
        if not descr:
            raise CommandError('Description is required')

        gw_addr = input('Address: ')
        if not gw_addr:
            raise CommandError('gateway address is required')

        start_usage_time = input('Start usage time in format "%s": ' % datetime_format)
        if not start_usage_time:
            raise CommandError("Start usage time is required, check format")

        gw_ip_addrs = input("Gateway comma separated ip addresses. <IPv4/[IPv6]>:<port>: ")
        if not gw_ip_addrs:
            raise CommandError("Gateway addrs is required")

        data, fname = _make_gateways_data(
            gw_type=gw_type,
            descr=descr,
            gw_addr=gw_addr,
            start_usage_time=datetime.strptime(start_usage_time, datetime_format),
            gw_ip_addrs=gw_ip_addrs
        )
        self.write2file(data=data)
        self.stdout.write(self.style.SUCCESS('OK'))

    def rm(self, val):
        gw_id = input('Gateway id: ')
        if not gw_id:
            raise CommandError('Gateway id is required')

        self.del_from_file(gw_id)
        self.stdout.write(self.style.SUCCESS('OK'))
