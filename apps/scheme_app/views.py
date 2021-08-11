import json

from django.conf import settings
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class MapSchemeAPIView(APIView):
    if getattr(settings, "DEBUG", False):
        from rest_framework.authentication import SessionAuthentication

        authentication_classes = (TokenAuthentication, SessionAuthentication)
    else:
        authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, IsAdminUser)

    @staticmethod
    def get(request, format=None):
        del format
        with open('scheme.json', 'r') as f:
            data = json.load(f)
        return Response(data)

    @staticmethod
    def post(request, format=None):
        data = request.data
        with open('scheme.json', 'w') as f:
            json.dump(data, f)
        return Response(status=status.HTTP_204_NO_CONTENT)
