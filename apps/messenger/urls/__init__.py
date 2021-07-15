from django.urls import path, include

from messenger.urls.viber import urlpatterns_viber

app_name = "messenger"


urlpatterns = [
    path("viber", include(urlpatterns_viber))
]
