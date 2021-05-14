from django.contrib.auth.models import Permission
from django.db import models, transaction
from guardian.ctypes import get_content_type
from guardian.shortcuts import assign_perm
from rest_framework.exceptions import AuthenticationFailed


class BaseAbstractModelMixin:
    def assign_rights2new_obj(self, request):
        user = request.user
        if not user:
            raise AuthenticationFailed
        user_groups = [grp for grp in user.groups.all()]
        if len(user_groups) == 0:
            return
        available_perms_for_new_object = Permission.objects.filter(content_type=get_content_type(self))
        with transaction.atomic():
            for perm in available_perms_for_new_object:
                for grp in user_groups:
                    assign_perm(perm, grp, self)


class BaseAbstractModel(BaseAbstractModelMixin, models.Model):
    class Meta:
        abstract = True
