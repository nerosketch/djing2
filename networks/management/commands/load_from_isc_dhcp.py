import os
import gzip

from django.core.management.base import BaseCommand, no_translations, CommandError
from isc_dhcp_leases import Lease, IscDhcpLeases
from isc_dhcp_leases.iscdhcpleases import _extract_properties, parse_time, Lease6

from networks.exceptions import DhcpRequestError
from networks.models import CustomerIpLeaseModel, parse_opt82, NetworkIpPool


class IscDhcpLeasesGen(IscDhcpLeases):
    def get_iter(self, include_backups=False):
        """
        Parse the lease file and return a generator of Lease instances.
        """
        with open(self.filename) if not self.gzip else gzip.open(self.filename) as lease_file:
            lease_data = lease_file.read()
            if self.gzip:
                lease_data = lease_data.decode('utf-8')
            for match in self.regex_leaseblock.finditer(lease_data):
                block = match.groupdict()

                properties, options, sets = _extract_properties(block['config'])

                if 'hardware' not in properties and not include_backups:
                    # E.g. rows like {'binding': 'state abandoned', ...}
                    continue
                yield Lease(block['ip'], properties=properties, options=options, sets=sets)

            for match in self.regex_leaseblock6.finditer(lease_data):
                block = match.groupdict()
                properties, options, sets = _extract_properties(block['config'])

                host_identifier = block['id']
                block_type = block['type']
                last_client_communication = parse_time(properties['cltt'])

                for address_block in self.regex_iaaddr.finditer(block['config']):
                    block = address_block.groupdict()
                    properties, options, sets = _extract_properties(block['config'])

                    yield Lease6(block['ip'], properties, last_client_communication, host_identifier, block_type,
                                   options=options, sets=sets)

    def _get_current_iter(self):
        """
        Parse the lease file and return a dict of active and valid Lease instances.
        The key for this dict is the ethernet address of the lease.
        """
        all_leases = self.get_iter()
        for lease in all_leases:
            if lease.valid and lease.active:
                if type(lease) is Lease:
                    yield lease.ethernet, lease
                    # leases[lease.ethernet] = lease
                elif type(lease) is Lease6:
                    yield '%s-%s' % (lease.type, lease.host_identifier_string), lease

    # def get_current_iter(self):
    #     return {x: v for x, v in self._get_current_iter()}


class Command(BaseCommand):
    help = "Loads ip leases from isc-dhcp-server leases file"

    def add_arguments(self, parser):
        parser.add_argument('leasefile', help='lease file absolute path', nargs=1, type=str)

    @staticmethod
    def _conv_param(p: bytes) -> bytearray:
        return bytearray(int(i, base=16) for i in p.split(b':'))

    @no_translations
    def handle(self, leasefile: list, *args, **options):
        leasefile = leasefile[0]
        if not(os.path.exists(leasefile) and os.path.isfile(leasefile)):
            raise CommandError('File "%s" does not exist' % leasefile)

        CustomerIpLeaseModel.objects.filter(is_dynamic=True).delete()

        leases = IscDhcpLeasesGen(leasefile)
        it_count = 0
        new_leases = []
        for mac, l in leases._get_current_iter():
            ex = l.data.get('execute')
            if isinstance(ex, str) and 'release' in ex:
                continue
            it_count += 1
            remote_id = l.options.get('agent.remote-id')
            circuit_id = l.options.get('agent.circuit-id')
            if not all([remote_id, circuit_id]):
                print('No', remote_id, circuit_id)
                continue
            remote_id = remote_id.encode()
            circuit_id = circuit_id.encode()
            if b'ZTE' in circuit_id:
                remote_id = remote_id.replace(b'"', b'')
                circuit_id = circuit_id.replace(b'"', b'')
            else:
                remote_id = self._conv_param(remote_id)
                circuit_id = self._conv_param(circuit_id)
            dev_mac, dev_port = parse_opt82(remote_id, circuit_id)

            # Find customer by device mac and device port
            customer_id = CustomerIpLeaseModel.find_customer_id_by_device_credentials(
                device_mac=dev_mac, device_port=dev_port
            )
            if not customer_id:
                print('Error: customer not found for:', dev_mac, dev_port)
                continue
            ip_pool = NetworkIpPool.find_ip_pool_by_ip(
                ip_addr=str(l.ip)
            )
            if ip_pool is None:
                print('Error: ip_pool not found for ip', l.ip)
                continue

            try:
                lease = CustomerIpLeaseModel(
                    ip_address=l.ip,
                    pool=ip_pool,
                    lease_time=l.start,
                    customer_id=customer_id,
                    mac_address=l.ethernet,
                    is_dynamic=True
                )
                new_leases.append(lease)
                print('Maked', lease)
            except DhcpRequestError as err:
                print('Err:', err)
        created_objs = CustomerIpLeaseModel.objects.bulk_create(
            objs=new_leases, batch_size=200
        )
        print('Count:', it_count, 'Created:', len(created_objs))
