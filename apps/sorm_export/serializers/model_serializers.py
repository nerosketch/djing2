from django.db.models import Count
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from groupapp.models import Group
from sorm_export.models import FiasRecursiveAddressModel


class FiasRecursiveAddressModelSerializer(serializers.ModelSerializer):
    ao_level_name = serializers.CharField(source='get_ao_level_display', read_only=True)
    ao_type_name = serializers.CharField(source='get_ao_type_display', read_only=True)
    parent_ao_name = serializers.CharField(source='parent_ao.title', read_only=True)

    def validate(self, attrs):
        """Group must have only one FiasRecursiveAddressModel.
        And specifying ForeignKey in Group model may be corrupt
        flexibility. So I did this validation here."""
        selected_group_ids = [sg.pk for sg in attrs.get('groups', [])]
        groups = Group.objects.filter(
            pk__in=selected_group_ids
        ).annotate(
            addrs_count=Count('fiasrecursiveaddressmodel')
        ).filter(addrs_count__gt=0)
        if groups.exists():
            raise ValidationError({
                'groups': _('Groups "%s" has more than one "FIAS" address type.') % ','.join(g.title for g in groups)
            })
        return attrs

    class Meta:
        model = FiasRecursiveAddressModel
        fields = '__all__'
