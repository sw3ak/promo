from django.conf import settings
from django.http import request as http_request

from receipts import promo as promo_config


def promo(unused_request: http_request.HttpRequest) -> dict:
    return {
        'promo_period': promo_config.get_period(),
        'promo_min_amount': promo_config.get_min_amount(),
        'promo_site_url': settings.PROMO_SITE_URL,
    }
