from types import GeneratorType
from rest_framework.renderers import BrowsableAPIRenderer
from drf_ujson.renderers import UJSONRenderer


class BrowsableAPIRendererNoForm(BrowsableAPIRenderer):
    def render_form_for_serializer(self, serializer):
        return None


class ExtendedUJSONRenderer(UJSONRenderer):
    def render(self, data, *args, **kwargs):
        if isinstance(data, GeneratorType):
            # TODO: May optimize it in ujson
            data = tuple(data)
        return super().render(data, *args, **kwargs)
