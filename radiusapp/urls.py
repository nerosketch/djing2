from rest_framework.routers import DefaultRouter
from .views import customers
from .views import networks

app_name = 'radiusapp'

router = DefaultRouter()

# customer radius views
router.register('customer', customers.RadiusCustomerServiceRequestViewSet, basename='customer')

# network radius api
router.register('network', networks.RadiusRequestViewSet, basename='network')
