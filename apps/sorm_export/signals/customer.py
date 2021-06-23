from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch.dispatcher import receiver

from customers.custom_signals import customer_service_post_pick
from customers.models import (
    Customer, PassportInfo, CustomerService,
    AdditionalTelephone
)
from sorm_export.hier_export.customer import export_individual_customer
from sorm_export.models import ExportFailedStatus
from sorm_export.tasks.customer import (
    customer_service_export_task,
    customer_service_manual_data_export_task,
    customer_contact_export_task, customer_root_export_task
)


@receiver(pre_save, sender=Customer)
def customer_pre_save_signal(sender, instance: Customer,
                             update_fields=None, **kwargs):
    if update_fields is None or bool({'telephone', 'fio', 'username'}.intersection(update_fields)):
        # all fields updated, or one of used fields is updated
        old_inst = sender.objects.filter(pk=instance.pk).first()
        if old_inst is None:
            return
        now = datetime.now()
        if old_inst.telephone != instance.telephone:
            # Tel has updated, signal it
            old_start_time = old_inst.last_update_time or datetime.combine(
                instance.create_date,
                datetime(year=now.year, month=1, minute=0, day=1, second=0, hour=0).time()
            )
            customer_tels = [{
                'customer_id': instance.pk,
                'contact': '%s %s' % (old_inst.get_full_name(), old_inst.telephone),
                'actual_start_time': old_start_time,
                'actual_end_time': now
            }, {
                'customer_id': instance.pk,
                'contact': '%s %s' % (instance.get_full_name(), instance.telephone),
                'actual_start_time': now,
                # 'actual_end_time':
            }]
            customer_contact_export_task(
                customer_tels=customer_tels,
                event_time=now
            )

        # export username if it changed
        if old_inst.username != instance.username:
            # username changed
            customer_root_export_task(
                customer_id=instance.pk,
                event_time=now
            )


@receiver(customer_service_post_pick, sender=Customer)
def customer_post_pick_service_signal_handler(sender, customer: Customer, service, **kwargs):
    if not customer.current_service_id:
        raise ExportFailedStatus('Customer has not current_service')

    # start service for customer
    customer_service_export_task(
        customer_service_id_list=[int(customer.current_service_id)],
        event_time=str(datetime.now())
    )


@receiver(post_save, sender=PassportInfo)
def customer_passport_info_post_save_signal(sender, instance: Optional[PassportInfo] = None,
                                            **kwargs):
    cs = Customer.objects.filter(passportinfo=instance)
    if cs.exists():
        export_individual_customer(
            customers=cs
        )


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
    srv = instance.service
    if hasattr(instance, 'customer'):
        dat = [{
            'service_id': srv.pk,
            'idents': instance.customer.pk,
            'parameter': srv.descr or str(srv),
            'begin_time': instance.start_time,
            'end_time': datetime.now()
        }]
        customer_service_manual_data_export_task(
            data=dat,
            event_time=str(datetime.now())
        )


# @receiver(post_save, sender=CustomerRawPassword)
# def customer_password_changed(sender, instance: Optional[CustomerRawPassword] = None,
#                              created=False, **kwargs):
#    pass


@receiver(pre_save, sender=AdditionalTelephone)
def customer_additional_telephone_post_save_signal(sender, instance: AdditionalTelephone,
                                                   **kwargs):
    customer = instance.customer
    customer_name = customer.get_full_name()
    contact = '%s(%s) %s' % (customer_name, instance.owner_name, instance.telephone)
    now = datetime.now()
    old_inst = sender.objects.filter(pk=instance.pk).first()
    if old_inst is None:
        # then its created
        customer_tels = [{
            'customer_id': customer.pk,
            'contact': contact,
            'actual_start_time': now,
            # 'actual_end_time':
        }]
    else:
        customer_tels = [{
            'customer_id': customer.pk,
            'contact': '%s(%s) %s' % (customer_name, old_inst.owner_name, old_inst.telephone),
            'actual_start_time': old_inst.create_time,
            'actual_end_time': now
        }, {
            'customer_id': customer.pk,
            'contact': contact,
            'actual_start_time': now,
            # 'actual_end_time':
        }]
    customer_contact_export_task(
        customer_tels=customer_tels,
        event_time=datetime.now()
    )


@receiver(pre_delete, sender=AdditionalTelephone)
def customer_additional_telephone_post_delete_signal(sender, instance: AdditionalTelephone, **kwargs):
    customer = instance.customer
    customer_name = customer.get_full_name()
    now = datetime.now()
    customer_tels = [{
        'customer_id': customer.pk,
        'contact': '%s(%s) %s' % (customer_name, instance.owner_name, instance.telephone),
        'actual_start_time': instance.create_time,
        'actual_end_time': now
    }]
    customer_contact_export_task(
        customer_tels=customer_tels,
        event_time=now
    )


# @receiver(post_save, sender=PeriodicPayForId)
# def customer_periodic_pay_post_save_signal(sender, instance: Optional[PeriodicPayForId] = None,
#                                           created=False, **kwargs):
#    pass
