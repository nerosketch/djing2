from django.urls import path, include
from rest_framework.routers import DefaultRouter
from addresses import views


app_name = 'addresses'

router = DefaultRouter()
router.register('', views.AddressModelViewSet)

urlpatterns = [
    path('autocomplete/', views.AddressAutocompleteAPIView.as_view()),
    path('', include(router.urls)),
]
