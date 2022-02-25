from django.urls import path, include
from django.conf import settings
from djing2.views import SearchApiView, can_login_by_location, get_vapid_public_key


api_urls = [
    path("profiles/", include("profiles.urls", namespace="profiles")),
    path("groups/", include("groupapp.urls", namespace="groups")),
    path("addrs/", include("addresses.urls", namespace="addresses")),
    path("services/", include("services.urls", namespace="services")),
    path("gateways/", include("gateways.urls", namespace="gateways")),
    path("devices/", include("devices.urls", namespace="devices")),
    path("customers/", include("customers.urls", namespace="customers")),
    path("customer_comments/", include("customer_comments.urls", namespace="customer_comments")),
    path("customer_contract/", include("customer_contract.urls", namespace="customer_contract")),
    path("messenger/", include("messenger.urls", namespace="messenger")),
    path("tasks/", include("tasks.urls", namespace="tasks")),
    path("networks/", include("networks.urls", namespace="networks")),
    path("dynamicfields/", include("dynamicfields.urls", namespace="dynamicfields")),
    path("fin/", include("fin_app.urls", namespace="fin_app")),
    path("sites/", include("sitesapp.urls", namespace="sitesapp")),
    path("radius/", include("radiusapp.urls", namespace="radiusapp")),
    path("sorm/", include("sorm_export.urls", namespace="sorm_export")),
    path("traf_stat/", include("traf_stat.urls", namespace="traf_stat")),
    path("legal/", include("customers_legal.urls", namespace="customers_legal")),
    path("can_login_by_location/", can_login_by_location),
    path("search/", SearchApiView.as_view()),
    path("webpush/", include("webpush.urls")),
    path("get_vapid_public_key/", get_vapid_public_key),
]


urlpatterns = [
    path("api/", include(api_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.contrib import admin
    from django.views.generic import TemplateView
    from rest_framework.schemas import get_schema_view

    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
    urlpatterns.extend(staticfiles_urlpatterns())
    urlpatterns.append(path("admin/", admin.site.urls))
    urlpatterns.append(path("api-auth/", include("rest_framework.urls")))
    urlpatterns.extend(
        [
            path(
                "openapi/",
                get_schema_view(
                    title="Djing2 project", description="Billing system for small internet providers", version="2.0.0"
                ),
                name="openapi-schema",
            ),
            path(
                "swagger-ui/",
                TemplateView.as_view(template_name="swagger-ui.html", extra_context={"schema_url": "openapi-schema"}),
                name="swagger-ui",
            ),
        ]
    )
