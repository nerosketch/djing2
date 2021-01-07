from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver

from customers.models import (
    Customer, PassportInfo, CustomerService,
    CustomerRawPassword, AdditionalTelephone,
    PeriodicPayForId
)
from sorm_export.tasks.customer import customer_service_export_task, customer_service_finish_export_task


@receiver(post_save, sender=Customer)
def customer_post_save_signal(sender, instance: Optional[Customer] = None,
                              created=False, update_fields=(), **kwargs):
    if 'current_service' in update_fields and instance.current_service:
        # start service for customer
        customer_service_export_task(
            customer_service_id_list=[instance.current_service.pk],
            event_time=str(datetime.now())
        )


@receiver(post_save, sender=PassportInfo)
def customer_passport_info_post_save_signal(sender, instance: Optional[PassportInfo] = None,
                                            created=False, **kwargs):
    pass


@receiver(post_save, sender=CustomerService)
def customer_service_changed(sender, instance: Optional[CustomerService] = None,
                             created=False, **kwargs):
    if created:
        # if created then customer also changed,
        # and customer change signal is also called
        return
    customer_service_export_task(
        customer_service_id_list=[instance.pk],
        event_time=str(datetime.now())
    )


@receiver(pre_delete, sender=CustomerService)
def customer_service_deleted(sender, instance: CustomerService, **kwargs):
    # customer service end of life
    if instance.customer:
        customer_service_finish_export_task(
            customer_service_id=instance.service.pk,
            customer_id=instance.customer.pk,
            srv_descr=instance.service.descr,
            srv_begin_time=instance.start_time,
            event_time=str(datetime.now())
        )


@receiver(post_save, sender=CustomerRawPassword)
def customer_password_changed(sender, instance: Optional[CustomerRawPassword] = None,
                              created=False, **kwargs):
    if created:
        return
    # process only if changed, not created


@receiver(post_save, sender=AdditionalTelephone)
def customer_additional_telephone_post_save_signal(sender, instance: Optional[AdditionalTelephone] = None,
                                                   created=False, **kwargs):
    pass


@receiver(post_save, sender=PeriodicPayForId)
def customer_periodic_pay_post_save_signal(sender, instance: Optional[PeriodicPayForId] = None,
                                           created=False, **kwargs):
    pass
