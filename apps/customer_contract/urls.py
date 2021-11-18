from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customer_contract import views


app_name = 'customer_contract'

router = DefaultRouter()
router.register('contract', views.CustomerContractModelViewSet)
router.register('docs', views.CustomerContractAttachmentModelViewSet)


urlpatterns = [
    path('', include(router.urls))
]
