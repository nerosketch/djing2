import dataclasses

from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class BrowsableAPIRendererNoForm(BrowsableAPIRenderer):
    def render_form_for_serializer(self, serializer):
        return None


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


class CustomJSONRenderer(JSONRenderer):
    encoder_class = CustomJSONEncoder
