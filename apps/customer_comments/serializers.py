from rest_framework import serializers
from customer_comments.models import CustomerCommentModel


class CustomerCommentModelSerializer(serializers.ModelSerializer):
    # customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    author_id = serializers.IntegerField(source="author.pk", read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_avatar = serializers.CharField(source="author.get_avatar_url", read_only=True)
    can_remove = serializers.SerializerMethodField(method_name='_can_remove')

    def _can_remove(self, comment):
        return self.context["request"].user.pk == comment.author_id

    class Meta:
        model = CustomerCommentModel
        exclude = ['author']
