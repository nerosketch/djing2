from rest_framework.urls import path

from scheme_app.views import MapSchemeAPIView

app_name = 'scheme_app'

urlpatterns = [
    path("", MapSchemeAPIView.as_view())
]
