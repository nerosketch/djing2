from django.urls import path, include
from messenger import views
from rest_framework.routers import DefaultRouter
from messenger.models.base_messenger import get_messenger_model_info_generator


router = DefaultRouter()
router.register('subscriber', views.SubscriberModelViewSet)

for type_name, messenger_uint, messenger_model_class in get_messenger_model_info_generator():
    tmp_viewset = views.MessengerModelViewSet
    tmp_viewset.queryset = messenger_model_class.objects.all()
    tmp_viewset.serializer_class.Meta.model = messenger_model_class
    router.register(type_name, tmp_viewset, basename=f'messenger-{type_name}')


app_name = "messenger"

urlpatterns = [
    path('get_bot_types/', views.get_bot_types),
    path('options/', views.NotificationProfileOptionsModelViewSet.as_view()),
    path('get_notification_options/', views.get_notification_options),
    path('get_notification_types/', views.get_notification_types),
    path("", include(router.urls)),
]
