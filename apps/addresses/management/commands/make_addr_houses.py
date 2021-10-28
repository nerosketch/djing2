from typing import Any

from django.core.management.base import BaseCommand
from addresses.models import AddressModel, AddressModelTypes
from customers.models import Customer


class Command(BaseCommand):
    help = "Copy add"

    def _proc_customer(self, customer: Customer):
        # берём всё что ниже назначенного адреса абонента,
        # и только то, что под улицей.
        """Копировать адрес абонента из простого текстового поля
        в адресную иерархию."""
        house = customer.house
        addr = customer.address
        if not house:
            self.stdout.write('')
            self.stdout.write("Customer {} not have value in house field. {}".format(customer, self.style.ERROR("Failed")))
            return
        if not addr:
            self.stdout.write('')
            self.stdout.write("Customer {} not have address. {}".format(customer, self.style.ERROR("Failed")))
            return
        new_house_addr, created = AddressModel.objects.get_or_create(
            title=str(house),
            parent_addr=addr,
            address_type=AddressModelTypes.HOUSE,
            fias_address_level=8,
            fias_address_type=803,
        )
        r = Customer.objects.filter(pk=customer.pk).update(address=new_house_addr)
        self.stdout.write("." if r > 0 else '!', ending='')

    def handle(self, *args: Any, **options: Any):
        for c in Customer.objects.all().iterator():
            self._proc_customer(c)
        self.stdout.write(self.style.SUCCESS("DONE"))
