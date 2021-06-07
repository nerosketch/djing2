from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sorm_export import views

app_name = 'sorm_export'

router = DefaultRouter()

router.register('addr', views.FiasRecursiveAddressModelViewSet)


urlpatterns = [
    # path('', views.ExportAPIView.as_view()),
    path('', include(router.urls)),
]
