from django.db.models.signals import pre_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from customers.models import Customer
# from customer_contract.tasks import create_customer_default_contract_task
from customer_contract.custom_signals import finish_customer_contract_signal
from customer_contract.models import CustomerContractModel


# @receiver(post_save, sender=Customer)
# def customer_profile_post_save(sender, instance: Customer, created=False, **kwargs):
#     if not created:
#         return
#     create_customer_default_contract_task(
#         customer_id=instance.pk,
#         start_service_time=instance.create_date,
#         contract_number=instance.username
#     )


@receiver(finish_customer_contract_signal, sender=CustomerContractModel)
def customer_profile_disable_after_contract_stop(sender, instance: CustomerContractModel, created=False, **kwargs):
    # disable customer account while stop his main contract
    if created:
        if not instance.is_active:
            raise ValidationError(_('Not allowed to create disabled contract'))
        return
    Customer.objects.filter(pk=instance.customer.pk).update(is_active=False)


@receiver(pre_save, sender=Customer)
def customer_profile_prevent_enable_if_contract_finished(sender, instance: Customer, created=False, **kwargs):
    # prevent enable profile if his contract is stopped
    if created:
        return
    inactive_contracts = CustomerContractModel.objects.filter(customer=instance, is_active=False)
    if inactive_contracts.exists() and instance.is_active:
        raise ValidationError(_('Prevent enable profile when it has inactive contracts'))

