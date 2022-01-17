from rest_framework_guardian.filters import ObjectPermissionsFilter
from rest_framework.filters import SearchFilter

from apps.djing2.lib import safe_int


class CustomObjectPermissionsFilter(ObjectPermissionsFilter):
    shortcut_kwargs = {
        "accept_global_perms": True,
    }


class CustomSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        # TODO: move 10 to settings
        qs = super().filter_queryset(request, queryset, view)
        search_str = request.query_params.get(self.search_param)
        if search_str is not None:
            search_len = request.query_params.get('search_len')
            if search_len:
                search_len = safe_int(search_len)
            else:
                search_len = 10
            qs = qs[:search_len]
        return qs
