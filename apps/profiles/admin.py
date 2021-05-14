from django.contrib import admin
from profiles import models

admin.site.register(models.BaseAccount)
admin.site.register(models.UserProfile)
admin.site.register(models.UserProfileLog)
