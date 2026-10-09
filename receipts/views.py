import mimetypes

from django import http
from django import shortcuts
from django.conf import settings
from django.core import paginator

from receipts import forms
from receipts import models
from receipts import promo
from receipts import ratelimit
from receipts import selectors
from receipts import serializers
from receipts import services

PAGE_SIZE = 10
REQUEST_OVERHEAD_BYTES = 64 * 1024
RATE_LIMIT_MESSAGE = (
    'Слишком много попыток регистрации. Подождите минуту и попробуйте снова.'
)


def cabinet(request: http.HttpRequest) -> http.HttpResponse:
    sort = selectors.parse_sort(request.GET.get('sort'))
    receipts = selectors.for_user(request.user, sort)
    pages = paginator.Paginator(receipts, PAGE_SIZE)
    page = pages.get_page(request.GET.get('page'))
    context = {
        'page': page,
        'page_range': pages.get_elided_page_range(
            page.number, on_each_side=1, on_ends=1
        ),
        'total': pages.count,
        'sort': sort,
        'columns': _sort_columns(sort),
        'poll_seconds': settings.RECEIPT_STATUS_POLL_SECONDS,
    }
    return shortcuts.render(request, 'receipts/cabinet.html', context)


def _sort_columns(current: str) -> list[dict]:
    columns = [
        ('purchased_at', 'Дата покупки'),
        ('status', 'Статус'),
        ('amount', 'Сумма чека'),
        ('registered_at', 'Дата регистрации'),
    ]
    result = []
    for key, title in columns:
        active = current.removeprefix('-') == key
        descending = current.startswith('-')
        next_sort = key if active and descending else f'-{key}'
        result.append(
            {
                'title': title,
                'sort': next_sort,
                'active': active,
                'descending': active and descending,
            }
        )
    return result


def register(request: http.HttpRequest) -> http.HttpResponse:
    if request.method == 'POST':
        return _submit(request)
    return _render_form(request, forms.ReceiptForm())


def _submit(request: http.HttpRequest) -> http.HttpResponse:
    as_json = _wants_json(request)
    max_bytes = settings.RECEIPT_PHOTO_MAX_BYTES + REQUEST_OVERHEAD_BYTES
    if _content_length(request) > max_bytes:
        message = 'Файл слишком большой.'
        if as_json:
            return _json_error(message, 'too_large', 413)
        return _render_form(request, forms.ReceiptForm(), message, status=413)
    limit = settings.RECEIPT_SUBMIT_RATE_LIMIT
    if not ratelimit.is_allowed(f'receipt-submit:{request.user.pk}', limit):
        if as_json:
            return _json_error(RATE_LIMIT_MESSAGE, 'rate_limited', 429)
        form = forms.ReceiptForm()
        return _render_form(request, form, RATE_LIMIT_MESSAGE, status=429)

    form = forms.ReceiptForm(request.POST, request.FILES)
    if not form.is_valid():
        if as_json:
            return _json_error(
                'Проверьте правильность заполнения полей.',
                'invalid',
                400,
                errors=_form_errors(form),
            )
        return _render_form(request, form, status=400)

    try:
        result = services.register_receipt(request.user, form.to_input())
    except services.RegistrationError as e:
        if as_json:
            return _json_error(e.message, e.code, 409)
        return _render_form(request, form, e.message, status=409)

    if as_json:
        return http.JsonResponse(
            {
                'message': 'Ваш чек загружен',
                'resubmitted': result.resubmitted,
                'receipt': serializers.receipt_to_dict(result.receipt),
            },
            status=201,
        )
    return shortcuts.redirect('receipts:success')


def _render_form(request, form, error: str = '', status: int = 200):
    context = {
        'form': form,
        'error': error,
        'period': promo.get_period(),
        'min_amount': promo.get_min_amount(),
        'photo_max_bytes': settings.RECEIPT_PHOTO_MAX_BYTES,
    }
    return shortcuts.render(
        request, 'receipts/register.html', context, status=status
    )


def _content_length(request: http.HttpRequest) -> int:
    try:
        return int(request.META.get('CONTENT_LENGTH') or 0)
    except ValueError:
        return 0


def _wants_json(request: http.HttpRequest) -> bool:
    return 'application/json' in request.headers.get('Accept', '')


def _form_errors(form) -> dict[str, list[str]]:
    return {
        field: [error['message'] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


def _json_error(message, code, status, errors=None) -> http.JsonResponse:
    return http.JsonResponse(
        {'message': message, 'code': code, 'errors': errors or {}},
        status=status,
    )


def success(request: http.HttpRequest) -> http.HttpResponse:
    return shortcuts.render(request, 'receipts/success.html')


def photo(request: http.HttpRequest, pk: int) -> http.FileResponse:
    receipts = models.Receipt.objects.exclude(photo='')
    if not request.user.has_perm('receipts.view_receipt'):
        receipts = receipts.filter(user=request.user)
    receipt = shortcuts.get_object_or_404(receipts, pk=pk)
    content_type, _ = mimetypes.guess_type(receipt.photo.name)
    try:
        file = receipt.photo.open('rb')
    except FileNotFoundError as e:
        raise http.Http404('Фото не найдено.') from e
    response = http.FileResponse(
        file, content_type=content_type or 'application/octet-stream'
    )
    response['Cache-Control'] = 'private, max-age=3600'
    return response
