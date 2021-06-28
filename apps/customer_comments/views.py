from djing2.viewsets import DjingModelViewSet
from rest_framework import status
from rest_framework.response import Response
from customer_comments.serializers import CustomerCommentModelSerializer
from customer_comments.models import CustomerCommentModel


class CustomerCommentModelViewSet(DjingModelViewSet):
    queryset = CustomerCommentModel.objects.select_related('customer', 'author').order_by('-id')
    serializer_class = CustomerCommentModelSerializer
    filterset_fields = ['customer']

    def create(self, request, *args, **kwargs):
        return super().create(request, author=self.request.user.pk, *args, **kwargs)

    def perform_create(self, *args, **kwargs):
        return super().perform_create(author=self.request.user, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        # if request.user.is_superuser and comment.author_id == request.user.pk:
        if comment.author_id == request.user.pk:
            self.perform_destroy(comment)
            return Response(status=status.HTTP_200_OK)

        return Response(_("You can't delete foreign comments"), status=status.HTTP_403_FORBIDDEN)
