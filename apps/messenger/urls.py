from django.urls import path, include

from .urls.viber import urlpatterns_viber

app_name = "messenger"


urlpatterns = [path("viber", include(urlpatterns_viber))]
