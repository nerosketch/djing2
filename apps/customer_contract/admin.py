from django.contrib import admin
from customer_contract import models


admin.site.register(models.CustomerContractModel)
admin.site.register(models.CustomerContractAttachmentModel)
