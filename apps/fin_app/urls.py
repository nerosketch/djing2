from django.urls import path, include
from rest_framework.routers import DefaultRouter
from fin_app.views import alltime
from fin_app.views import rncb
from fin_app.views import payme

app_name = "fin_app"


router = DefaultRouter()
# router.register("base/log", base.BasePaymentLogModelViewSet)
# router.register("base", base.BasePaymentGatewayModelViewSet)

router.register("alltime/log", alltime.AllTimePayLogModelViewSet)
router.register("alltime", alltime.AllTimeGatewayModelViewSet)

# router.register("rncb/log", rncb.RNCBPayLogModelViewSet)
# router.register("rncb", rncb.PayRNCBGatewayModelViewSet)

router.register("payme/log", payme.PaymeLogModelViewSet)
router.register("payme", payme.PaymePaymentGatewayModelViewSet)

urlpatterns = [
    path("alltime/<slug:pay_slug>/pay/", alltime.AllTimePay.as_view()),
    # path("rncb/<slug:pay_slug>/pay/", rncb.RNCBPaymentViewSet.as_view()),
    path("payme/<slug:pay_slug>/pay/", payme.PaymePaymentEndpoint.as_view()),
    path("", include(router.urls)),
]
