from django.db.models import Count
from djing2.viewsets import DjingModelViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from fin_app.models.base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel,
    report_by_pays
)
from fin_app.serializers.base import (
    BasePaymentModelSerializer,
    BasePaymentLogModelSerializer,
    PaysReportParamsSerializer,
)


class BasePaymentGatewayModelViewSet(DjingModelViewSet):
    queryset = BasePaymentModel.objects.order_by('id').annotate(
        pay_count=Count("basepaymentlogmodel")
    )
    serializer_class = BasePaymentModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        raise ValidationError("Base payment model can't direct creation")

    @action(methods=['get'], detail=False)
    def pays_report(self, request):
        ser = PaysReportParamsSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        dat = ser.data
        r = report_by_pays(
            from_time=dat.get('from_time'),
            to_time=dat.get('to_time'),
            pay_gw_id=dat.get('pay_gw'),
            group_by=dat.get('group_by', 0),
            limit=dat.get('limit')
        )
        return Response(list(r))


class BasePaymentLogModelViewSet(DjingModelViewSet):
    queryset = BasePaymentLogModel.objects.all()
    serializer_class = BasePaymentLogModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        raise ValidationError("Base payment log can't direct creation")
