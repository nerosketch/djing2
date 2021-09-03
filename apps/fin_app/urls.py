from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fin_app.views import alltime

app_name = "fin_app"


router = DefaultRouter()
router.register("log", alltime.AllTimePayLogModelViewSet)
router.register("", alltime.AllTimeGatewayModelViewSet)

urlpatterns = [
    path("<slug:pay_slug>/pay/", alltime.AllTimePay.as_view()),
    path("", include(router.urls)),
]
