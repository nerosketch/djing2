from django.urls import path, include
from messenger import views
from rest_framework.routers import DefaultRouter
from messenger.models.base_messenger import get_messenger_model_info_generator


router = DefaultRouter()
router.register('subscriber', views.SubscriberModelViewSet)


#
# Generate and register viewsets for different messenger types
#
bvs = views.MessengerModelViewSet
for type_name, messenger_uint, messenger_model_class in get_messenger_model_info_generator():
    tmp_viewset = type('tmp_viewset', bvs.__bases__, dict(bvs.__dict__))
    tmp_viewset.queryset = messenger_model_class.objects.filter(bot_type=messenger_uint)
    tmp_viewset.serializer_class.Meta.model = messenger_model_class
    router.register(type_name, tmp_viewset, basename=f'messenger-{type_name}')
del bvs, tmp_viewset, type_name, messenger_uint, messenger_model_class

app_name = "messenger"

urlpatterns = [
    path('get_bot_types/', views.get_bot_types),
    path('options/', views.NotificationProfileOptionsModelViewSet.as_view()),
    path("", include(router.urls)),
]
