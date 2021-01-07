from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver

from customers.models import (
    Customer, PassportInfo, CustomerService,
    CustomerRawPassword, AdditionalTelephone,
    PeriodicPayForId
)
from sorm_export.tasks.customer import (
    customer_service_export_task,
    customer_service_manual_data_export_task
)


@receiver(post_save, sender=Customer)
def customer_post_save_signal(sender, instance: Optional[Customer] = None,
                              created=False, update_fields=None, **kwargs):
    if update_fields is not None and 'current_service' in update_fields and instance.current_service:
        # start service for customer
        customer_service_export_task(
            customer_service_id_list=[instance.current_service.pk],
            event_time=str(datetime.now())
        )


@receiver(post_save, sender=PassportInfo)
def customer_passport_info_post_save_signal(sender, instance: Optional[PassportInfo] = None,
                                            created=False, **kwargs):
    pass


# Called when customer extends his service
# @receiver(continue_service_signal, sender=CustomerService)
# def customer_service_autoconnected(sender, instance: CustomerService,
#                                    old_instance_data: CustomerService,
#                                    **kwargs):
#     # auto continue customer service
#     now = datetime.now()
#     data = [
#         {
#             # old service info
#             'service_id': old_instance_data['service'],
#             'idents': old_instance_data['customer'],
#             'parameter': old_instance_data['service_descr'],
#             'begin_time': old_instance_data['start_time'],
#             'end_time': now
#         },
#         {
#             # new service info
#             'service_id': instance.service.pk,
#             'idents': instance.customer.pk,
#             'parameter': instance.service.descr,
#             'begin_time': instance.start_time,
#             'end_time': instance.deadline
#         }
#     ]
#     customer_service_manual_data_export_task(
#         data=data,
#         event_time=now
#     )


@receiver(pre_delete, sender=CustomerService)
def customer_service_deleted(sender, instance: CustomerService, **kwargs):
    # customer service end of life
    if instance.customer:
        dat = [{
            'service_id': instance.service.pk,
            'idents': instance.customer.pk,
            'parameter': instance.service.descr,
            'begin_time': instance.start_time,
            'end_time': datetime.now()
        }]
        customer_service_manual_data_export_task(
            data=dat,
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
