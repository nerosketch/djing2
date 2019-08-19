from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fin_app import views

app_name = 'fin_app'


router = DefaultRouter()
router.register('', views.AllTimeGatewayModelViewSet)

urlpatterns = [
    path('pay/', views.AllTimePay.as_view()),
    path('', include(router.urls)),
]
