from typing import Set
from django.db.models.signals import m2m_changed
from django.dispatch.dispatcher import receiver
from djing2.lib import LogicError
from customers_legal.models import CustomerLegalModel


@receiver(m2m_changed, sender=CustomerLegalModel.branches.through)
def customer_branches_pre_save_signal(sender, instance: CustomerLegalModel, action: str, model, pk_set: Set[int], **kwargs):
    if action != 'pre_add':
        return

    legal_contract_date = instance.actual_start_time
    new_customers = model.objects.filter(pk__in=pk_set)
    for new_customer in new_customers:
        for contract in new_customer.customercontractmodel_set.all():
            if contract.start_service_time != legal_contract_date:
                raise LogicError('Дата заключения договора подразделения(абонента) ЮЛ не совпадает с датой начала договора ЮЛ. '
                        'Это соответствие обязательно для СОРМ. Филиал(абонент): "%s", договор: "%s", ЮЛ: "%s"' % (
                    new_customer.get_full_name(), contract.title, instance.title
                ))
