import decimal

from django.conf import settings
from django.core import checks


def check_promo_settings(
    app_configs=None, **kwargs
) -> list[checks.CheckMessage]:
    errors = []
    if settings.PROMO_START_DATE > settings.PROMO_END_DATE:
        errors.append(
            checks.Error(
                'PROMO_START_DATE is later than PROMO_END_DATE.',
                hint='Check the promo dates in .env.',
                id='receipts.E001',
            )
        )
    if settings.PROMO_MIN_AMOUNT <= decimal.Decimal(0):
        errors.append(
            checks.Error(
                'PROMO_MIN_AMOUNT must be positive.', id='receipts.E002'
            )
        )
    if settings.RECEIPT_MAX_RESUBMISSIONS < 0:
        errors.append(
            checks.Error(
                'RECEIPT_MAX_RESUBMISSIONS must not be negative.',
                id='receipts.E003',
            )
        )
    if settings.RECEIPT_PHOTO_MAX_BYTES <= 0:
        errors.append(
            checks.Error(
                'RECEIPT_PHOTO_MAX_MB must be positive.', id='receipts.E004'
            )
        )
    return errors
