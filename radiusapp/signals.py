from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_delete

from djing2.lib import safe_int
from networks.models import CustomerIpLeaseModel
from radiusapp.models import CustomerRadiusSession
from radiusapp import tasks
from customers import custom_signals as customer_custom_signals
from customers.models import Customer, CustomerService


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def try_stop_session_too_signal(sender, instance, **kwargs):
    sess = CustomerRadiusSession.objects.filter(ip_lease=instance).first()
    if sess:
        sess.finish_session()


@receiver(customer_custom_signals.customer_service_pre_stop,
          sender=CustomerService,
          dispatch_uid='on_pre_stop_cust_srv%&6')
def on_pre_stop_cust_srv_signal(sender, expired_service, **kwargs):
    print('#'*80)
    print('on_pre_stop_cust_srv')
    print('#' * 80)
    tasks.radius_stop_customer_session_task(
        customer_id=expired_service.customer_id
    )


# @receiver(customer_custom_signals.customer_service_post_stop,
#           sender=CustomerService, dispatch_uid='on_post_stop_cust_srv*&5^')
# def on_post_stop_cust_srv_signal(sender, expired_service, **kwargs):
#     print('#' * 80)
#     print('on_post_stop_cust_srv')
#     print('#' * 80)


@receiver(customer_custom_signals.customer_service_pre_pick,
          sender=Customer, dispatch_uid='on_pre_pick_cust_srv*$@0')
def on_pre_pick_cust_srv_signal(sender, customer, service, **kwargs):
    print('#' * 80)
    print('on_pre_pick_cust_srv', customer, service)
    print('#' * 80)
    tasks.radius_stop_customer_session_task(
        customer_id=customer.pk
    )


# @receiver(customer_custom_signals.customer_service_post_pick,
#           sender=Customer, dispatch_uid='on_post_pick_cust_srv&!_&')
# def on_post_pick_cust_srv_signal(sender, customer, service, **kwargs):
#     print('#' * 80)
#     print('on_post_pick_cust_srv', customer, service)
#     print('#' * 80)


@receiver(customer_custom_signals.customer_service_batch_pre_stop,
          sender=CustomerService,
          dispatch_uid='on_pre_batch_stop_customer_services&$@(7')
def on_pre_batch_stop_customer_services_signal(sender, expired_services, **kwargs):
    print('#' * 80)
    print('on_pre_batch_stop_customer_services_signal', expired_services)
    print('#' * 80)
    customer_ids = (safe_int(es.customer_id) for es in expired_services.iterator())
    customer_ids = tuple(i for i in customer_ids if i > 0)
    tasks.radius_batch_stop_customer_services_task(
        customer_ids=customer_ids
    )


# @receiver(customer_custom_signals.customer_service_batch_post_stop,
#           sender=CustomerService,
#           dispatch_uid='on_pre_batch_stop_customer_services*@#^4')
# def on_post_batch_stop_customer_services_signal(sender, expired_services, **kwargs):
#     print('#' * 80)
#     print('on_post_batch_stop_customer_services_signal', expired_services)
#     print('#' * 80)
