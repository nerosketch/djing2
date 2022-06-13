from types import GeneratorType
import json
from django.core.serializers.json import DjangoJSONEncoder
from orjson import orjson
from rest_framework.renderers import BrowsableAPIRenderer
from drf_orjson_renderer.renderers import ORJSONRenderer


class BrowsableAPIRendererNoForm(BrowsableAPIRenderer):
    def render_form_for_serializer(self, serializer):
        return None


class ExtendedRenderer(ORJSONRenderer):
    @staticmethod
    def default(obj):
        if isinstance(obj, bytes):
            return obj.decode()
        elif hasattr(obj, '__str__'):
            return str(obj)
        elif isinstance(obj, (set, GeneratorType)):
            return list(obj)
        return ORJSONRenderer.default(obj=obj)

    def render(self, data, media_type=None, renderer_context=None):
        """
        Serializes Python objects to JSON.

        :param data: The response data, as set by the Response() instantiation.
        :param media_type: If provided, this is the accepted media type, of the
                `Accept` HTTP header.
        :param renderer_context: If provided, this is a dictionary of contextual
                information provided by the view. By default this will include
                the following keys: view, request, response, args, kwargs
        :return: bytes() representation of the data encoded to UTF-8
        """
        if data is None:
            return b''

        renderer_context = renderer_context or {}

        # By default, this function will use its own version of `default()` in
        # order to safely serialize known Django types like QuerySets. If you
        # know you won't need this you can pass `None` to the renderer_context
        # ORJSON will only serialize native Python built-in types. If you know
        # that you need to serialize additional types such as Numpy you can
        # override the default here.
        #
        # Instead of the full if-else, the temptation here is to optimize
        # this block by calling:
        #
        # `default = renderer_context.get("default_function", self.default)`
        #
        # Don't do that here because you will lose the ability to pass `None`
        # to ORJSON.
        if "default_function" not in renderer_context:
            default = self.default
        else:
            default = renderer_context["default_function"]

        # If `indent` is provided in the context, then pretty print the result.
        # E.g. If we're being called by RestFramework's BrowsableAPIRenderer.
        indent = renderer_context.get("indent")
        if indent is None or "application/json" in media_type:
            serialized = orjson.dumps(
                data, default=default, option=self.options
            )
        else:
            encoder_class = DjangoJSONEncoder
            serialized = json.dumps(data, indent=indent, cls=encoder_class, ensure_ascii=True)
        return serialized
