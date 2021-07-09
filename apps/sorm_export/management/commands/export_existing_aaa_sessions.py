import csv
import sys
from netfields.mac import mac_unix_common

from django.core.management.base import BaseCommand
from radiusapp.models import CustomerRadiusSession
from rest_framework.utils.serializer_helpers import ReturnList
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType


class Command(BaseCommand):
    help = "Exports all active aaa sessions 2 СОРМ"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fname', type=str, help='Writes result into this file'
        )

    def handle(self, fname=None, *args, **options):
        sessions = CustomerRadiusSession.objects.exclude(customer=None).defer(
            'last_event_time', 'session_duration', 'input_packets', 'output_packets', 'closed'
        ).select_related('customer', 'ip_lease').iterator()

        dat = [{
            "event_time": ses.assign_time,
            "event_type": AAAEventType.RADIUS_AUTH_START,
            "session_id": str(ses.session_id),
            "customer_ip": ses.ip_lease.ip_address,
            "customer_db_username": ses.customer.get_username(),
            "customer_device_mac": ses.ip_lease.mac_address.format(dialect=mac_unix_common) if ses.ip_lease.mac_address else '00:00:00:00:00'
        } for ses in sessions]

        ser = AAAExportSerializer(data=dat, many=True)
        ser.is_valid(raise_exception=True)

        print(ser.data[0], type(ser.data))
        lines = [v for v in ser.data]
        print('Lines:', lines)

        if fname is None:
            csv_writer = csv.writer(sys.stdout, dialect="unix", delimiter=";")
            csv_writer.writerows(lines)
        else:
            with open(fname, "a") as f:
                csv_writer = csv.writer(f, dialect="unix", delimiter=";")
                csv_writer.writerows(lines)

        self.stdout.write('Result writes to "%s" ', ending='')
        self.stdout.write(self.style.SUCCESS('OK'))
