from django.db import models
from django.utils.translation import gettext_lazy as _
from customers.models import Customer
from profiles.models import UserProfile


class CustomerCommentModel(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    author = models.ForeignKey(UserProfile, verbose_name=_("Author"), on_delete=models.CASCADE)
    text = models.TextField(_("Text"))
    date_create = models.DateTimeField(_("Comment time"), auto_now_add=True)

    def __str__(self):
        return self.text

    class Meta:
        db_table = "customer_comments"
