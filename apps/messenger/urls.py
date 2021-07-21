from django.urls import path, include
from messenger import views
from rest_framework.routers import DefaultRouter
from messenger.models.base_messenger import get_messenger_model_info_generator


router = DefaultRouter()
router.register('subscriber', views.SubscriberModelViewSet)

for type_name, messenger_uint, messenger_model_class in get_messenger_model_info_generator():
    viewset_with_qs = views.MessengerModelViewSet
    viewset_with_qs.queryset = messenger_model_class.objects.all()
    router.register(type_name, viewset_with_qs, basename=f'messenger-{type_name}')


app_name = "messenger"

urlpatterns = [
    path('get_bot_types/', views.get_bot_types),
    path("", include(router.urls)),
]
