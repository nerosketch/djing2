from typing import Optional

from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from customers.models import (
    Customer, PassportInfo, CustomerService,
    CustomerRawPassword, AdditionalTelephone,
    PeriodicPayForId
)


@receiver(post_save, sender=Customer)
def customer_post_save_signal(sender, instance: Optional[Customer]=None,
                              created=False, **kwargs):
    pass


@receiver(post_save, sender=PassportInfo)
def customer_passport_info_post_save_signal(sender, instance: Optional[PassportInfo]=None,
                                            created=False, **kwargs):
    pass


@receiver(post_save, sender=CustomerService)
def customer_service_changed(sender, instance: Optional[CustomerService]=None,
                             created=False, **kwargs):
    if created:
        # if created then customer also changed,
        # and customer change signal is also called
        return


@receiver(post_save, sender=CustomerRawPassword)
def customer_password_changed(sender, instance: Optional[CustomerRawPassword]=None,
                              created=False, **kwargs):
    if created:
        return
    # process only if changed, not created


@receiver(post_save, sender=AdditionalTelephone)
def customer_additional_telephone_post_save_signal(sender, instance: Optional[AdditionalTelephone]=None,
                                                   created=False, **kwargs):
    pass


@receiver(post_save, sender=PeriodicPayForId)
def customer_periodic_pay_post_save_signal(sender, instance: Optional[PeriodicPayForId]=None,
                                           created=False, **kwargs):
    pass
