from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from customers.models import Customer
from customer_contract.tasks import create_customer_default_contract_task


@receiver(post_save, sender=Customer)
def customer_profile_post_save(sender, instance: Customer, created=False, **kwargs):
    if not created:
        return
    create_customer_default_contract_task(
        customer_id=instance.pk,
        start_service_time=instance.create_date,
        contract_number=instance.username
    )
