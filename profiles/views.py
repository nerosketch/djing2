from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.generics import RetrieveUpdateDestroyAPIView, ListCreateAPIView

from rest_framework.response import Response
from rest_framework import status

from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer
from djing2.metadata import FieldMetadata


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    metadata_class = FieldMetadata

    # def create(self, request, *args, **kwargs):
    #     print('create')
    #     serializer = self.get_serializer(data=request.data)
    #     if serializer.is_valid():
    #         self.perform_create(serializer)
    #         headers = self.get_success_headers(serializer.data)
    #         print('create Response')
    #         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
def test_req(req):
    if req.method == 'POST':
        print(req, req.POST)
    return HttpResponse('Ok request')


class UserProfileCreate(ListCreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class UserProfileDetails(RetrieveUpdateDestroyAPIView):
    model = UserProfile
    lookup_field = 'username'
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class UserProfileLogViewSet(viewsets.ModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
    metadata_class = FieldMetadata
