import hashlib

from django import http
from django.core import paginator
from django.db.models import aggregates
from django.utils import cache

from receipts import models
from receipts import selectors
from receipts import serializers

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
MAX_IDS = 100


class _BadRequestError(ValueError):
    pass


def receipt_list(request: http.HttpRequest) -> http.HttpResponse:
    if request.method != 'GET':
        return http.HttpResponseNotAllowed(['GET'])
    if not request.user.is_authenticated:
        return _error('Требуется авторизация.', 401)
    try:
        receipts, page_number, page_size = _filtered(request)
    except _BadRequestError as e:
        return _error(str(e), 400)

    etag = _etag(request, receipts)
    not_modified = cache.get_conditional_response(request, etag=etag)
    if not_modified is not None:
        return not_modified

    pages = paginator.Paginator(receipts, page_size)
    try:
        page = pages.page(page_number)
    except paginator.EmptyPage:
        return _error('Страница не найдена.', 404)
    response = http.JsonResponse(
        {
            'count': pages.count,
            'page': page.number,
            'page_size': page_size,
            'num_pages': pages.num_pages,
            'results': [serializers.receipt_to_dict(r) for r in page],
        },
        json_dumps_params={'ensure_ascii': False},
    )
    response['ETag'] = etag
    response['Cache-Control'] = 'private, no-cache'
    response['Vary'] = 'Cookie'
    return response


def _filtered(request):
    params = request.GET
    receipts = selectors.for_user(
        request.user, selectors.parse_sort(params.get('sort'))
    )
    status = params.get('status')
    if status:
        if status not in models.Receipt.Status.values:
            raise _BadRequestError('Неизвестный статус.')
        receipts = receipts.filter(status=status)
    ids = params.get('ids')
    if ids:
        receipts = receipts.filter(pk__in=_parse_ids(ids))
    page_number = _positive_int(params.get('page'), 1, 'page')
    page_size = _positive_int(
        params.get('page_size'), DEFAULT_PAGE_SIZE, 'page_size'
    )
    if page_size > MAX_PAGE_SIZE:
        raise _BadRequestError(
            f'page_size не может быть больше {MAX_PAGE_SIZE}.'
        )
    return receipts, page_number, page_size


def _parse_ids(raw: str) -> list[int]:
    parts = [part.strip() for part in raw.split(',') if part.strip()]
    if len(parts) > MAX_IDS or not all(p.isdigit() for p in parts):
        raise _BadRequestError(
            f'ids - до {MAX_IDS} числовых идентификаторов через запятую.'
        )
    return [int(part) for part in parts]


def _positive_int(raw: str | None, default: int, name: str) -> int:
    if raw in (None, ''):
        return default
    if not raw.isdigit() or int(raw) < 1:
        raise _BadRequestError(f'{name} должен быть положительным числом.')
    return int(raw)


def _etag(request, receipts) -> str:
    stats = receipts.order_by().aggregate(
        count=aggregates.Count('id'), last=aggregates.Max('updated_at')
    )
    last = stats['last'].isoformat() if stats['last'] else '-'
    key = f'{request.user.pk}|{request.get_full_path()}|{stats["count"]}|{last}'
    return f'"{hashlib.sha256(key.encode()).hexdigest()[:32]}"'


def _error(message: str, status: int) -> http.JsonResponse:
    return http.JsonResponse(
        {'detail': message},
        status=status,
        json_dumps_params={'ensure_ascii': False},
    )
