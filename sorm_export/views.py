from datetime import datetime, timedelta, date

from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from djing2.lib.renderer import BrowsableAPIRendererNoForm
from sorm_export.csv_renderer import CSVRenderer
from sorm_export.models import Choice4BooleanField, CustomerTypeChoices, CustomerDocumentTypeChoices
from sorm_export.serializers.individual_entity_plain_serializers import CustomerExportPlainFormat


dat = [
    {
        # 'communication_standard': 1,
        'customer_id': '234',
        'customer_login': '123123sd',
        'contract_number': 'aiusodaiuosd',
        'current_state': Choice4BooleanField.YES,
        'contract_start_date': datetime.now(),
        'contract_end_date': datetime.now() + timedelta(days=4),
        'customer_type': CustomerTypeChoices.INDIVIDUAL_ENTITY,
        'name_structured_type': Choice4BooleanField.NO,
        'not_structured_name': 'My long name',
        'birthday': date(year=1993, month=2, day=28),
        'passport_type_structured': Choice4BooleanField.NO,
        'passport_serial': '3514',
        'passport_number': '3914926',
        'passport_date': date(year=2014, month=7, day=12),
        'passport_distributor': 'ФМС МВД',
        'document_type': CustomerDocumentTypeChoices.PASSPORT_RF
    },
]


class ExportAPIView(APIView):
    serializer_class = CustomerExportPlainFormat
    renderer_classes = [BrowsableAPIRendererNoForm, JSONRenderer, CSVRenderer]
    http_method_names = ['get']

    # def get_serializer(self, *args, **kwargs):

    def get(self, request, *args, **kwargs):
        ser = self.serializer_class(data=dat, many=True)
        ser.is_valid(raise_exception=True)
        return Response(ser.data)
