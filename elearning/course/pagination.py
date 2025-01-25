from rest_framework.pagination import PageNumberPagination

class CoursePagination(PageNumberPagination):
    page_size = 9  # Number of courses per page
    page_size_query_param = 'page_size'  # Allow user to set custom page size
    max_page_size = 100  # Set a maximum limit for page size
