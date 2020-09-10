from rest_framework_guardian.filters import ObjectPermissionsFilter


class CustomObjectPermissionsFilter(ObjectPermissionsFilter):
    shortcut_kwargs = {
        'accept_global_perms': True,
    }
