from django.urls import path
# from rest_framework.routers import DefaultRouter
from sorm_export import views

app_name = 'sorm_export'

# router = DefaultRouter()

# router.register('', )


urlpatterns = [
    path('', views.ExportAPIView.as_view()),
    # path('', include(router.urls)),
]
