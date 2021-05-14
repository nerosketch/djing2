from rest_framework.renderers import BrowsableAPIRenderer


class BrowsableAPIRendererNoForm(BrowsableAPIRenderer):
    def render_form_for_serializer(self, serializer):
        return None
