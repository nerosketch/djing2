from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_save, pre_delete
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext

from djing2.lib import LogicError
from djing2.lib.logger import logger
from customers.models import Customer, CustomerService, AdditionalTelephone
from customers.custom_signals import customer_turns_on
from sorm_export.models import ExportFailedStatus
from sorm_export.tasks.customer import (
    customer_service_manual_data_export_task,
    customer_contact_export_task,
)
#  from customer_contract.custom_signals import finish_customer_contract_signal
from customer_contract.models import CustomerContractModel
from sorm_export.checks.customer import (
    customer_checks,
    customer_legal_branch_checks,
)


#def reexport_customer_with_new_contract(customer, event_time: datetime):
#    """Завершение учётки со старой датой, и выгрузка с новой.
#       Когда изменяется логин, дата актуальности, и.т.д. То для
#       сохранения историчности данных сначала выгружаем учётку
#       со старыми данными, с датой завершения договора сейчас,
#       и ещё раз но только с датой старта договора сейчас, и не определённой
#       датой завершения договора.
#    """
#    customers_qs = general_customer_filter_queryset().filter(pk=customer.pk)
#
#    # ---------------------------------------------------------------------------------------------------------------
#    # 1) - Выгружаем окончание действия текущего абонента
#
#    # Выгружаем корневую запись по абоненту.
#    # Тут нет даты окончания действия, так что выгружем
#    #  CustomerRootExportTree(recursive=True).exportNupload(queryset=customers_qs)
#
#    # Точка подключения абонента, с датой окончания интервала на котором актульна информация - сейчас.
#    AccessPointExportTree(
#        event_time=event_time,
#        extra_kwargs={
#            'actual_end_time': event_time
#        }
#    ).exportNupload(
#        queryset=customers_qs
#    )
#
#    # Физический абонент
#    IndividualCustomersExportTree(event_time=event_time).exportNupload(
#        queryset=
#    )
#
#    # Выгружаем контакт
#    ContactSimpleExportTree(event_time=event_time).exportNupload(data=customer_tels, many=True)
#
#    # Договор абонента
#    CustomerContractExportTree(event_time=event_time).exportNupload(
#        queryset=
#    )
#
#    # ---------------------------------------------------------------------------------------------------------------
#    # 2) - Выгружаем новое начало действия абонента. (Как бы нового абонента).
#
#    # Точка подключения абонента, с датой начала интервала на котором актульна информация - сейчас,
#    # и не указанной датой окончания интервала.
#    AccessPointExportTree(
#        event_time=event_time,
#        extra_kwargs={
#            'actual_start_time': event_time
#        }
#    ).exportNupload(
#        queryset=customers_qs
#    )
#    # Обновить дату начала в БД
#    contract = customer.customercontractmodel_set.update()

def on_customer_change(instance: Customer):
    old_instance = Customer.objects.filter(pk=instance.pk).first()
    if old_instance is None:
        # if old instance does not exists, then it is new instance, just skip
        return
    if old_instance.username != instance.username:
        raise LogicError(_('Changing username is forbidden due to СОРМ rules'))



#def on_customer_fields_change(sender, instance, old_inst):
#    """Если изменяются поля абонента, то запускаем по ним задачи эксопрта в сорм"""
#
#    now = datetime.now()
#    if old_inst.telephone != instance.telephone:
#        # Tel has updated, signal it
#        # TODO: Test it
#        old_start_time = old_inst.last_update_time or datetime.combine(
#            instance.create_date,
#            datetime(year=now.year, month=1, day=1, hour=0, minute=0, second=0).time()
#        )
#        customer_tels = [
#            {
#                "customer_id": instance.pk,
#                "contact": f"{old_inst.get_full_name()} {old_inst.telephone}",
#                "actual_start_time": old_start_time,
#                "actual_end_time": now,
#            },
#            {
#                "customer_id": instance.pk,
#                "contact": f"{instance.get_full_name()} {instance.telephone}",
#                "actual_start_time": now,
#                # 'actual_end_time':
#            },
#        ]
#        customer_contact_export_task(customer_tels=customer_tels, event_time=now)
#
#    # export username if it changed
#    if old_inst.username != instance.username:
#        # username changed, prevent it
#        # TODO: Test it
#        url = 'https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_hier:start'
#        raise ExportFailedStatus(
#            gettext("Customer username changing is prevented due to SORM rules [%(url)s]") % url
#        )


@receiver(pre_save, sender=Customer)
def customer_pre_save_signal(sender, instance: Customer, update_fields=None, **kwargs):
    #  required_fields = {"telephone", "fio", "username"}
    on_customer_change(instance)

    #if update_fields is None or bool({"telephone", "fio", "username"}.intersection(update_fields)):
    #    # all fields updated, or one of used fields is updated
    #    old_instance = sender.objects.filter(pk=instance.pk).first()
    #    if old_instance is None:
    #        return
    #    on_customer_fields_change(sender=sender, instance=instance, old_inst=old_instance)


@receiver(pre_delete, sender=Customer)
def prevent_delete_customer_due2eol_export(sender, instance, **kwargs):
    """Если удалить учётную запись абонента то по нему не выгрузятся
       данные для СОРМ3."""

    raise ExportFailedStatus(
        gettext("Prevent to remove customer profile due to sorm export")
    )


#@receiver(post_save, sender=Customer)
#def customer_post_save_signal(sender, instance: Customer, created=False, **kwargs):
#    if created:
#        # export customer root record
#        customer_root_export_task(customer_id=instance.pk, event_time=datetime.now())


#@receiver(customer_service_post_pick, sender=Customer)
#def customer_post_pick_service_signal_handler(sender, customer: Customer, service, **kwargs):
#    if not customer.current_service_id:
#        raise ExportFailedStatus("Customer has not current_service")
#
#    # start service for customer
#    customer_service_export_task(
#        customer_service_id_list=[int(customer.current_service_id)], event_time=datetime.now()
#    )


#@receiver(post_save, sender=PassportInfo)
#def customer_passport_info_post_save_signal(sender, instance: Optional[PassportInfo] = None, **kwargs):
#    cs = Customer.objects.filter(passportinfo=instance)
#
#    exporter = IndividualCustomersExportTree(recursive=True)
#    data = exporter.export(queryset=cs)
#    exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.CUSTOMER_INDIVIDUAL)
#
#    if cs.exists():
#        export_individual_customers_queryset(customers_queryset=cs)


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
        customer_service_manual_data_export_task(data=dat, event_time=datetime.now())


# @receiver(post_save, sender=CustomerRawPassword)
# def customer_password_changed(sender, instance: Optional[CustomerRawPassword] = None,
#                              created=False, **kwargs):
#    pass


@receiver(pre_save, sender=AdditionalTelephone)
def customer_additional_telephone_post_save_signal(sender, instance: AdditionalTelephone, **kwargs):
    customer = instance.customer
    customer_name = customer.get_full_name()
    contact = f"{customer_name}({instance.owner_name}) {instance.telephone}"
    now = datetime.now()
    old_inst = sender.objects.filter(pk=instance.pk).first()
    if old_inst is None:
        # then its created
        customer_tels = [
            {
                "customer_id": customer.pk,
                "contact": contact,
                "actual_start_time": instance.create_time,
                'actual_end_time': None
            }
        ]
    else:
        customer_tels = [
            {
                "customer_id": customer.pk,
                "contact": f"{customer_name}({old_inst.owner_name}) {old_inst.telephone}",
                "actual_start_time": old_inst.create_time,
                "actual_end_time": now,
            },
            {
                "customer_id": customer.pk,
                "contact": contact,
                "actual_start_time": now,
                'actual_end_time': None
            },
        ]
    instance.create_time = now
    customer_contact_export_task(customer_tels=customer_tels, event_time=datetime.now())


@receiver(pre_delete, sender=AdditionalTelephone)
def customer_additional_telephone_post_delete_signal(sender, instance: AdditionalTelephone, **kwargs):
    customer = instance.customer
    customer_name = customer.get_full_name()
    now = datetime.now()
    customer_tels = [
        {
            "customer_id": customer.pk,
            "contact": f"{customer_name}({instance.owner_name}) {instance.telephone}",
            "actual_start_time": instance.create_time,
            "actual_end_time": now,
        }
    ]
    customer_contact_export_task(customer_tels=customer_tels, event_time=now)


# @receiver(post_save, sender=PeriodicPayForId)
# def customer_periodic_pay_post_save_signal(sender, instance: Optional[PeriodicPayForId] = None,
#                                           created=False, **kwargs):
#    pass


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


#@receiver(customer_turns_off, sender=Customer)
#def on_customer_turns_off(sender, instance: Customer, **kwargs):
#    logger.info("on_customer_turns_off")

