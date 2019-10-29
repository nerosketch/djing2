from rest_framework.pagination import PageNumberPagination

from djing2.lib import safe_int


class QueryPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_page_size(self, request):
        try:
            q_page_size = safe_int(request.query_params[self.page_size_query_param])
            if q_page_size > 0:
                return q_page_size
        except (KeyError, ValueError):
            pass
        return self.max_page_size
