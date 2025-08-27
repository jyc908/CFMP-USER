from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """默认每页20个，最多100个"""

    page_size = 20
    page_query_param = "page"
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "links": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "count": self.page.paginator.count if self.page else 0,
                "total_pages": self.page.paginator.num_pages if self.page else 0,
                "current_page": self.page.number if self.page else 0,
                "results": data,
            }
        )