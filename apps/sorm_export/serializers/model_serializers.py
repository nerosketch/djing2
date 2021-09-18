from django.db.models import Count
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from addresses.models import LocalityModel
from sorm_export.models import FiasRecursiveAddressModel


class FiasRecursiveAddressModelSerializer(serializers.ModelSerializer):
    ao_level_name = serializers.CharField(source='get_ao_level_display', read_only=True)
    ao_type_name = serializers.CharField(source='get_ao_type_display', read_only=True)
    parent_ao_name = serializers.CharField(source='parent_ao.title', read_only=True)

    def validate(self, attrs):
        """Group must have only one FiasRecursiveAddressModel.
        And specifying ForeignKey in Group model may be corrupt
        flexibility. So I did this validation here."""
        selected_localities_ids = [locality.pk for locality in attrs.get('localities', [])]
        if len(selected_localities_ids) < 1:
            return attrs
        localities = LocalityModel.objects.filter(
            pk__in=selected_localities_ids
        ).annotate(
            addrs_count=Count('fiasrecursiveaddressmodel')
        ).filter(addrs_count__gt=0)
        if localities.exists():
            raise ValidationError({
                'localities': _('Localities "%s" has more than one "FIAS" address type.')
                              % ','.join(locality.title for locality in localities)
            })
        return attrs

    class Meta:
        model = FiasRecursiveAddressModel
        fields = '__all__'
