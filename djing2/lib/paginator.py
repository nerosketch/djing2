from rest_framework.pagination import PageNumberPagination


class QueryPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
