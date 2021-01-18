from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sorm_export import views

app_name = 'sorm_export'

router = DefaultRouter()

router.register('level', views.FIASAddressLevelModelViewSet)
router.register('types', views.FIASAddressTypeModelViewSet)
router.register('coutry', views.FiasCountryModelViewSet)
router.register('region', views.FiasRegionModelViewSet)
router.register('group', views.GroupFIASInfoModelViewSet)


urlpatterns = [
    # path('', views.ExportAPIView.as_view()),
    path('', include(router.urls)),
]
