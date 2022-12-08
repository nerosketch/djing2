from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends, Query, Path
from services.models import CustomerServiceConnectingQueueModel, Service
from services.schemas import CustomerServiceQueueModelSchema
from starlette import status

router = APIRouter(
    prefix='/queue',
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/pending/{customer_id}/',
            response_model=list[CustomerServiceQueueModelSchema],
            dependencies=[Depends(permission_check_dependency(
                perm_codename='services.view_customerserviceconnectingqueuemodel'
            ))]
            )
def get_service_queue_for_customer(
    customer_id: int = Path(gt=0)
):
    qs = CustomerServiceConnectingQueueModel.objects.filter(
        customer=customer_id
    ).select_related('service')
    return [CustomerServiceQueueModelSchema.from_orm(i) for i in qs.iterator()]


@router.post('/pending/{customer_id}/swap/',
             dependencies=[Depends(permission_check_dependency(
                 perm_codename='services.change_customerserviceconnectingqueuemodel'
             ))],
             status_code=status.HTTP_204_NO_CONTENT
             )
def swap_queue_items(customer_id: int = Path(gt=0),
                     queue_id1: int = Query(gt=0), queue_id2: int = Query(gt=0)):
    queue1 = get_object_or_404(CustomerServiceConnectingQueueModel, pk=queue_id1)
    queue2 = get_object_or_404(CustomerServiceConnectingQueueModel, pk=queue_id2)
    CustomerServiceConnectingQueueModel.objects.filter(
        customer_id=customer_id
    ).swap(
        first=queue1,
        second=queue2
    )


@router.post('/{queue_item_id}/append/',
             dependencies=[Depends(permission_check_dependency(
                 perm_codename='services.add_customerserviceconnectingqueuemodel'
             ))],
             response_model=CustomerServiceQueueModelSchema
             )
def append(queue_item_id: int = Path(gt=0), service_id: int = Query(gt=0)):
    qitem = get_object_or_404(CustomerServiceConnectingQueueModel, pk=queue_item_id)
    service = get_object_or_404(Service, pk=service_id)
    new_item = qitem.append(s=service)
    return CustomerServiceQueueModelSchema.from_orm(new_item)


@router.post('/{queue_item_id}/prepend/',
             dependencies=[Depends(permission_check_dependency(
                 perm_codename='services.add_customerserviceconnectingqueuemodel'
             ))],
             response_model=CustomerServiceQueueModelSchema
             )
def prepend(queue_item_id: int = Path(gt=0), service_id: int = Query(gt=0)):
    qitem = get_object_or_404(CustomerServiceConnectingQueueModel, pk=queue_item_id)
    service = get_object_or_404(Service, pk=service_id)
    new_item = qitem.prepend(s=service)
    return CustomerServiceQueueModelSchema.from_orm(new_item)
