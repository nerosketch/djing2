import csv
from netfields.mac import mac_unix_common
from datetime import datetime

from django.core.management.base import BaseCommand, no_translations
from radiusapp.models import CustomerRadiusSession
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType
from sorm_export.ftp_worker.func import send_file2ftp
from sorm_export.hier_export.base import format_fname


class Command(BaseCommand):
    help = "Exports all active aaa sessions 2 СОРМ"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fname', type=str, help='Writes result into this file'
        )
        parser.add_argument(
            '--send2ftp',
            action='store_true',
            help='Send result 2 ftp, if --fname is specified'
        )

    @no_translations
    def handle(self, fname=None, send2ftp=None, *args, **options):
        sessions = CustomerRadiusSession.objects.exclude(customer=None).only(
            'customer', 'assign_time', 'session_id', 'ip_lease',
            'input_octets', 'output_octets'
        ).select_related('customer', 'ip_lease').iterator()

        dat = [{
            "event_time": ses.assign_time,
            "event_type": AAAEventType.RADIUS_AUTH_START,
            "session_id": str(ses.session_id),
            "customer_ip": ses.ip_lease.ip_address,
            "customer_db_username": ses.customer.get_username(),
            'input_octets': ses.input_octets,
            'output_octets': ses.output_octets,
            "customer_device_mac": ses.ip_lease.mac_address.format(dialect=mac_unix_common) if ses.ip_lease.mac_address else ''
        } for ses in sessions]

        ser = AAAExportSerializer(data=dat, many=True)
        ser.is_valid(raise_exception=True)

        lines_gen = ((v for k, v in i.items()) for i in ser.data)

        if fname is None:
            csv_writer = csv.writer(self.stdout, dialect="unix", delimiter=";")
            csv_writer.writerows(lines_gen)
            return

        with open(fname, "w") as f:
            csv_writer = csv.writer(f, dialect="unix", delimiter=";")
            csv_writer.writerows(lines_gen)

        self.stdout.write('Result writes ', ending='')
        self.stdout.write(self.style.SUCCESS('OK'))

        if send2ftp:
            now = datetime.utcnow()
            send_file2ftp(fname=fname, remote_fname=f"ISP/aaa/aaa_v1_{format_fname(now)}.txt")
            self.stdout.write('FTP Store ', ending='')
            self.stdout.write(self.style.SUCCESS('OK'))
