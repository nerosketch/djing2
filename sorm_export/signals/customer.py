from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch.dispatcher import receiver

from customers.models import (
    Customer, PassportInfo, CustomerService,
    CustomerRawPassword, AdditionalTelephone,
    PeriodicPayForId
)
from sorm_export.tasks.customer import (
    customer_service_export_task,
    customer_service_manual_data_export_task,
    customer_contact_export_task
)


@receiver(pre_save, sender=Customer)
def customer_post_save_signal(sender, instance: Optional[Customer] = None,
                              update_fields=None, **kwargs):
    if update_fields is None:
        # all fields updated
        old_inst = Customer.objects.filter(pk=instance.pk).first()
        if old_inst is not None and old_inst.telephone != instance.telephone:
            # Tel has updated, signal it
            customer_name = instance.get_full_name()
            tel = instance.telephone
            now = datetime.now()
            old_start_time = old_inst.last_update_time or datetime.combine(
                instance.create_date,
                datetime(year=now.year, month=1, minute=0, day=1, second=0, hour=0).time()
            )
            customer_tels = [{
                'customer_id': instance.pk,
                'contact': '%s %s' % (customer_name, tel),
                'actual_start_time': old_start_time,
                'actual_end_time': now
            }, {
                'customer_id': instance.pk,
                'contact': '%s %s' % (customer_name, tel),
                'actual_start_time': now,
                # 'actual_end_time':
            }]
            customer_contact_export_task(
                customer_tels=customer_tels,
                event_time=now
            )
    elif 'current_service' in update_fields and instance.current_service:
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
