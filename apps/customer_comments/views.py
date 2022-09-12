from django.utils.translation import gettext as _
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import NOT_FOUND
from fastapi import APIRouter, Depends
from starlette import status
from customer_comments.models import CustomerCommentModel
from starlette.exceptions import HTTPException
from starlette.responses import Response

from .schemas import CustomerCommentModelSchema, CustomerCommentModelBaseSchema


router = APIRouter(
    prefix='/customer_comments',
    tags=['CustomerComments'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/', response_model=list[CustomerCommentModelSchema])
# TODO: check rights for actions
def get_all_comments(customer: int, is_auth=Depends(is_admin_auth_dependency)):
    user, token = is_auth
    qs = CustomerCommentModel.objects.filter(
        customer_id=customer,
    ).select_related("customer", "author").order_by("-id")

    def _b(cmt):
        cmt.can_remove = user.pk == cmt.author_id
        c = CustomerCommentModelSchema.from_orm(cmt)
        return c

    return (_b(c) for c in qs)


@router.post('/', response_model=CustomerCommentModelSchema, status_code=status.HTTP_201_CREATED)
def create_customer_comment(comment: CustomerCommentModelBaseSchema, is_auth=Depends(is_admin_auth_dependency)):
    user, token = is_auth
    new_comment = CustomerCommentModel.objects.create(**comment.dict(), author_id=user.pk)
    new_comment.can_remove = user.pk == new_comment.author_id
    return CustomerCommentModelSchema.from_orm(new_comment)


@router.delete('/{comment_id}/', status_code=status.HTTP_204_NO_CONTENT)
def del_customer_comment(comment_id: int, is_auth=Depends(is_admin_auth_dependency)):
    try:
        comment = CustomerCommentModel.objects.get(pk=comment_id)
        user, token = is_auth
        if comment.author_id == user.pk:
            comment.delete()
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        raise HTTPException(status.HTTP_403_FORBIDDEN, _("You can't delete foreign comments"))

    except CustomerCommentModel.DoesNotExist:
        raise NOT_FOUND
