from django.db.models import query

from receipts import models

DEFAULT_SORT = '-registered_at'
SORT_FIELDS = {
    'purchased_at': 'purchased_at',
    'status': 'status',
    'amount': 'amount',
    'registered_at': 'registered_at',
}


def parse_sort(value: str | None) -> str:
    value = (value or '').strip()
    field = value.removeprefix('-')
    if field not in SORT_FIELDS:
        return DEFAULT_SORT
    return value


def for_user(user, sort: str = DEFAULT_SORT) -> query.QuerySet:
    sort = parse_sort(sort)
    descending = sort.startswith('-')
    field = SORT_FIELDS[sort.removeprefix('-')]
    order = [
        f'-{field}' if descending else field,
        '-id' if descending else 'id',
    ]
    return models.Receipt.objects.filter(user=user).order_by(*order)
