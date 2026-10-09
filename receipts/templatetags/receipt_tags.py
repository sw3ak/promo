import decimal

from django import template
from django.utils import http

register = template.Library()

_NBSP = ' '


def rub(value) -> str:
    if value in (None, ''):
        return ''
    amount = decimal.Decimal(value).quantize(decimal.Decimal('0.01'))
    integer, fraction = f'{amount:,.2f}'.split('.')
    integer = integer.replace(',', _NBSP)
    if fraction == '00':
        return f'{integer}{_NBSP}₽'
    return f'{integer},{fraction}{_NBSP}₽'


def page_query(context, **params) -> str:
    query = context['request'].GET.copy()
    for key, value in params.items():
        if value in (None, ''):
            query.pop(key, None)
        else:
            query[key] = value
    return http.urlencode(sorted(query.items()))


register.filter('rub', rub)
register.simple_tag(page_query, takes_context=True)
