from datetime import datetime
from django.conf import settings
from django.utils.translation import gettext
from uwsgi_tasks import task, TaskExecutor
# from djing2.lib import LogicError

from customers.models import Customer
from customer_contract.models import CustomerContractModel


@task(executor=TaskExecutor.SPOOLER)
def create_customer_default_contract_task(customer_id: int, start_service_time: datetime, contract_number: str):
    customer = Customer.objects.get(pk=customer_id)
    contracts_options = getattr(settings, 'CONTRACTS_OPTIONS', {})
    default_title = contracts_options.get('DEFAULT_TITLE', 'Contract default title')
    CustomerContractModel.objects.create(
        customer=customer,
        start_service_time=start_service_time,
        contract_number=contract_number,
        title=gettext(default_title),
    )
