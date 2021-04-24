from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from rest_framework import status
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from sitesapp.serializers import SiteSerializer


class SiteModelViewSet(DjingModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(_("Removing sites is temporary forbidden"), status=status.HTTP_405_METHOD_NOT_ALLOWED)
