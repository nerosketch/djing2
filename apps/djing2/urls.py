from django.urls import path, include
from django.conf import settings


api_urls = [
    path("profiles/", include("profiles.urls", namespace="profiles")),
    path("groups/", include("groupapp.urls", namespace="groups")),
    path("services/", include("services.urls", namespace="services")),
    path("gateways/", include("gateways.urls", namespace="gateways")),
    path("devices/", include("devices.urls", namespace="devices")),
    path("customers/", include("customers.urls", namespace="customers")),
    # path("messenger/", include("messenger.urls", namespace="messenger")),
    path("tasks/", include("tasks.urls", namespace="tasks")),
    path("networks/", include("networks.urls", namespace="networks")),
    path("dynamicfields/", include("dynamicfields.urls", namespace="dynamicfields")),
    path("fin/", include("fin_app.urls", namespace="fin_app")),
    path("sites/", include("sitesapp.urls", namespace="sitesapp")),
    path("traf_stat/", include("traf_stat.urls", namespace="traf_stat")),
    path("legal/", include("customers_legal.urls", namespace="customers_legal")),
    #path("hook/", include("webhooks.urls", namespace="webhooks")),
    path("webpush/", include("webpush.urls")),
]


urlpatterns = [
    path("api/", include(api_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.contrib import admin

    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
    urlpatterns.extend(staticfiles_urlpatterns())
    urlpatterns.append(path("admin/", admin.site.urls))
    urlpatterns.append(path("api-auth/", include("rest_framework.urls")))
