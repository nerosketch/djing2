# from collections import OrderedDict
#
# from rest_framework import serializers
# from rest_framework.fields import SkipField
# from rest_framework.relations import PKOnlyObject


# class VerboseModelSerializer(serializers.ModelSerializer):
#     def to_representation(self, instance):
#         ret = OrderedDict()
#         fields = self._readable_fields
#         for field in fields:
#             try:
#                 attribute = field.get_attribute(instance)
#             except SkipField:
#                 continue
#             check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
#             if check_for_none is None:
#                 ret[field.field_name] = None
#             else:
#                 ret[field.field_name] = {
#                     'v': field.to_representation(attribute),
#                     'i': {
#                         'help_text': getattr(field, 'help_text'),
#                         'label': getattr(field, 'label'),
#                         # 'max_length': getattr(field, 'max_length', 0),
#                         # 'required': getattr(field, 'required', False),
#                         # 'type': field.__class__.__name__
#                     }
#                 }
#         return ret
