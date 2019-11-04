from django.urls import path, include
from rest_framework.routers import DefaultRouter
from services.views import admin_side, user_side

app_name = 'services'


router = DefaultRouter()

# User side
router.register('user', user_side.UserSideServiceModelViewSet)

# Admin side
router.register('shot', admin_side.OneShotModelViewSet)
router.register('periodic', admin_side.PeriodicPayModelViewSet)
router.register('', admin_side.ServiceModelViewSet)

urlpatterns = [
    path('', include(router.urls))
]
