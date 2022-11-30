from customers.models import Customer
from djing2 import celery_app
from djing2.lib import LogicError
from djing2.lib.logger import logger
from services import periodicity_controllers


def customer_check_service_for_expiration(customer_id: int):
    """
    Finish expired services and connect new services if enough money
    :param customer_id: customers.customer.Customer primary key
    :return: nothing
    """
    try:
        customer = Customer.objects.get(pk=customer_id)
        if customer.auto_renewal_service:
            if customer.active_service():
                periodicity_controllers.continue_services_if_autoconnect(customer=customer)
            else:
                periodicity_controllers.connect_service_if_autoconnect(customer_id=customer_id)
        else:
            periodicity_controllers.finish_services_if_expired(customer=customer)

    except Customer.DoesNotExist:
        pass
    except LogicError as err:
        logger.error(str(err))


@celery_app.task
def customer_check_service_for_expiration_task(customer_id: int):
    customer_check_service_for_expiration(customer_id=customer_id)


@celery_app.task
def manage_services():
    periodicity_controllers.continue_services_if_autoconnect()
    periodicity_controllers.finish_services_if_expired()

    # Post connect service.
    periodicity_controllers.connect_service_if_autoconnect()

    periodicity_controllers.manage_periodic_pays_run()


celery_app.add_periodic_task(
    600, manage_services.s(), name='Manage customer services every 10 min'
)
