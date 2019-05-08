from django.urls import path, include
from django.conf import settings


urlpatterns = [
    path('profiles/', include('profiles.urls', namespace='profiles')),
    path('groups/', include('groupapp.urls', namespace='groups')),
    path('api-auth/', include('rest_framework.urls'))
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.contrib import admin

    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
    urlpatterns.extend(staticfiles_urlpatterns())
    urlpatterns.append(path('admin/', admin.site.urls))
