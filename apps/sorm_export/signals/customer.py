from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_save, pre_delete
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext

from djing2.lib import LogicError
from customers.models import Customer
from services.models import CustomerService
from customers.custom_signals import customer_turns_on
from sorm_export.models import ExportFailedStatus
from sorm_export.tasks.customer import (
    customer_service_manual_data_export_task,
)
from customer_contract.models import CustomerContractModel
from sorm_export.checks.customer import (
    customer_checks,
    customer_legal_branch_checks,
)


def on_customer_change(instance: Customer):
    old_instance = Customer.objects.filter(pk=instance.pk).first()
    if old_instance is None:
        # if old instance does not exists, then it is new instance, just skip
        return
    if old_instance.username != instance.username:
        raise LogicError(_('Changing username is forbidden due to СОРМ rules'))


@receiver(pre_save, sender=Customer)
def customer_pre_save_signal(sender, instance: Customer, update_fields=None, **kwargs):
    #  required_fields = {"telephone", "fio", "username"}
    on_customer_change(instance)


@receiver(pre_delete, sender=Customer)
def prevent_delete_customer_due2eol_export(sender, instance, **kwargs):
    """Если удалить учётную запись абонента то по нему не выгрузятся
       данные для СОРМ3."""

    raise ExportFailedStatus(
        gettext("Prevent to remove customer profile due to sorm export")
    )


@receiver(pre_delete, sender=CustomerService)
def customer_service_deleted(sender, instance: CustomerService, **kwargs):
    # customer service end of life
    # srv = instance.service
    if hasattr(instance, "customer"):
        dat = [
            {
                "service_id": 1,  # srv.pk,
                "idents": instance.customer.pk,
                "parameter": "Услуга высокоскоростного доступа в интернет",  # srv.descr or str(srv),
                "begin_time": instance.start_time,
                "end_time": datetime.now(),
            }
        ]
        customer_service_manual_data_export_task.delay(
            data=dat,
            event_time=datetime.now().timestamp()
        )


@receiver(pre_save, sender=CustomerContractModel)
def on_customer_contract_api_save(sender, instance: CustomerContractModel, **kwargs):
    old_instance = CustomerContractModel.objects.filter(pk=instance.pk).first()
    if old_instance is None:
        # if old instance does not exists, then it is new instance, just skip
        return
    if old_instance.start_service_time != instance.start_service_time:
        raise LogicError('Изменение даты начала договора запрещено правилами выгрузки СОРМ')
    if old_instance.contract_number != instance.contract_number:
        raise LogicError('Изменение номера договора запрещено правилами выгрузки СОРМ')


@receiver(customer_turns_on, sender=Customer)
def on_customer_turns_on(sender, instance: Customer, **kwargs):
    """Check is customer has all necessary info for exporting to СОРМ"""

    # check is customer is legal
    if instance.customerlegalmodel_set.exists():
        # customer is legal
        customer_legal_branch_checks(customer_branch=instance)
    else:
        # customer is individual
        customer_checks(customer=instance)


@receiver(pre_delete, sender=CustomerContractModel)
def on_customer_contract_delete(sender, instance: CustomerContractModel, **kwargs):
    raise LogicError('Запрещено удалять договор абонента, можно только завершить его. СОРМ')
