from django.conf import settings
from django.core.paginator import Paginator


def paginate(post_list, request):
    page_number = request.GET.get('page')
    paginator = Paginator(post_list, settings.PAGINATE_LIMIT)
    return paginator.get_page(page_number)
