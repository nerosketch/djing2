import math
from datetime import timedelta, date, datetime

from django.db import models, connection
from django.utils.timezone import now

from djing2.lib import safe_int
from djing2.models import BaseAbstractModel


class TrafficArchiveManager(models.Manager):
    @staticmethod
    def get_chart_data(customer_id: int, start_date: datetime, end_date: datetime = None) -> list:
        customer_id = safe_int(customer_id)
        if end_date is None:
            end_date = datetime.now()

        def _parse_vals(vals):
            str_time, octsum, pctsum = vals[1:-1].split(',')
            return {
                'time': datetime.strptime(str_time, '"%Y-%m-%d %H:%M:%S"'),
                'octsum': int(octsum),
                'pctsum': int(pctsum)
            }

        with connection.cursor() as cur:
            cur.execute("SELECT traf_fetch_archive4graph(%s::bigint, %s, %s);",
                        [customer_id, start_date, end_date])
            res = [_parse_vals(j) for r in cur.fetchall() for j in r]
        return res


class TrafficArchiveModel(BaseAbstractModel):
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE)
    event_time = models.DateTimeField()
    octets = models.PositiveIntegerField(default=0)
    packets = models.PositiveIntegerField(default=0)

    objects = TrafficArchiveManager()

    # ReadOnly
    def save(self, *args, **kwargs):
        pass

    # ReadOnly
    def delete(self, *args, **kwargs):
        pass

    @staticmethod
    def percentile(N, percent, key=lambda x: x):
        """
        Find the percentile of a list of values.

        @parameter N - is a list of values. Note N MUST BE already sorted.
        @parameter percent - a float value from 0.0 to 1.0.
        @parameter key - optional key function to compute value from each element of N.

        @return - the percentile of the values
        """
        if not N:
            return None
        k = (len(N) - 1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return key(N[int(k)])
        d0 = key(N[int(f)]) * (c - k)
        d1 = key(N[int(c)]) * (k - f)
        return d0 + d1

    @staticmethod
    def create_db_partitions():
        with connection.cursor() as cur:
            cur.execute("SELECT create_traf_archive_partition_tbl(now()::timestamp);")
            cur.fetchone()
            cur.execute("SELECT create_traf_archive_partition_tbl(now()::timestamp + '1 week'::interval);")
            cur.fetchone()

    class Meta:
        db_table = 'traf_archive'
        unique_together = ['customer', 'event_time']


class TrafficCache(BaseAbstractModel):
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE)
    event_time = models.DateTimeField()
    ip_addr = models.GenericIPAddressField()
    octets = models.PositiveIntegerField(default=0)
    packets = models.PositiveIntegerField(default=0)

    def is_online(self):
        return self.last_time > now() - timedelta(minutes=55)

    def is_today(self):
        return date.today() == self.last_time.date()

    def octets_to(self, to='m', bsize=1024):
        """convert octets <bytes> to megabytes, etc.
           sample code:
               print('mb= ' + str(bytesto(314575262000000, 'm')))
           sample output:
               mb= 300002347.946
           to:
        :param to: may be one of k m g t p e
        :param bsize: byte size
        """
        a = {'k': 1, 'm': 2, 'g': 3, 't': 4, 'p': 5, 'e': 6}
        r = float(self.octets)
        for i in range(a[to]):
            r = r / bsize
        return r

    class Meta:
        db_table = 'traf_cache'
        # db_tablespace = 'ram'
        ordering = '-event_time',
        unique_together = ['customer', 'ip_addr']
