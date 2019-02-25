from rest_framework.metadata import SimpleMetadata
from rest_framework.relations import RelatedField, ManyRelatedField


class FieldMetadata(SimpleMetadata):

    def get_field_info(self, field):
        field_info = super().get_field_info(field)
        if issubclass(field.__class__, (RelatedField, ManyRelatedField)):
            field_info['choices'] = field.get_choices()
        return field_info
