from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fin_app.views import alltime
from fin_app.views import rncb

app_name = "fin_app"


router = DefaultRouter()
router.register("alltime/log", alltime.AllTimePayLogModelViewSet)
router.register("alltime", alltime.AllTimeGatewayModelViewSet)

router.register("rncb/log", rncb.RNCBPayLogModelViewSet)
router.register("rncb", rncb.PayRNCBGatewayModelViewSet)

urlpatterns = [
    path("alltime/<slug:pay_slug>/pay/", alltime.AllTimePay.as_view()),
    path("rncb/<slug:pay_slug>/pay/", rncb.RNCBPaymentViewSet.as_view()),
    path("", include(router.urls)),
]
