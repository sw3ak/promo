import datetime
import decimal
import re

from django.core import exceptions
from django.utils import timezone

from receipts import models
from receipts import promo

PHOTO_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}
MAX_UTC_OFFSET = datetime.timedelta(hours=14)
MAX_AMOUNT = decimal.Decimal('99999999.99')

_SPACES = re.compile(r'[\s ]+')
_DIGITS = re.compile(r'^[0-9]+$')
_AMOUNT = re.compile(r'^[0-9]+(?:[.,][0-9]{1,2})?$')

ValidationError = exceptions.ValidationError


def strip_spaces(value: str) -> str:
    return _SPACES.sub('', value or '')


def clean_fn(value: str) -> str:
    value = strip_spaces(value)
    if not _DIGITS.match(value) or len(value) != models.FN_LENGTH:
        raise ValidationError('ФН состоит ровно из 16 цифр.', code='invalid_fn')
    return value


def clean_fiscal_int(value: str, label: str) -> int:
    value = strip_spaces(value)
    if not _DIGITS.match(value) or len(value) > 10:
        raise ValidationError(
            f'{label} - число до 10 цифр.', code='invalid_fiscal_number'
        )
    number = int(value)
    if not 1 <= number <= models.FISCAL_INT_MAX:
        raise ValidationError(
            f'{label} должен быть от 1 до {models.FISCAL_INT_MAX}.',
            code='invalid_fiscal_number',
        )
    return number


def parse_amount(value: str) -> decimal.Decimal:
    value = strip_spaces(value).replace('₽', '')
    if not _AMOUNT.match(value):
        raise ValidationError(
            'Введите сумму в рублях, например 1500 или 1500.50.',
            code='invalid_amount',
        )
    amount = decimal.Decimal(value.replace(',', '.'))
    if amount > MAX_AMOUNT:
        raise ValidationError('Слишком большая сумма.', code='invalid_amount')
    return amount.quantize(decimal.Decimal('0.01'))


def validate_min_amount(amount: decimal.Decimal) -> None:
    minimum = promo.get_min_amount()
    if amount < minimum:
        raise ValidationError(
            f'Минимальная сумма чека - {minimum:,.0f} ₽.'.replace(',', ' '),
            code='amount_too_small',
        )


def wall_clock(value: datetime.datetime) -> datetime.datetime:
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.replace(tzinfo=None)


def validate_purchased_at(
    value: datetime.datetime, now: datetime.datetime | None = None
) -> None:
    local = wall_clock(value)
    now = now or timezone.now()
    latest = (now.astimezone(datetime.UTC) + MAX_UTC_OFFSET).replace(
        tzinfo=None
    )
    if local > latest:
        raise ValidationError(
            'Дата покупки не может быть в будущем.', code='purchase_in_future'
        )
    period = promo.get_period()
    if not period.contains(local.date()):
        raise ValidationError(
            'Покупка должна быть совершена в период акции: '
            f'с {period.start:%d.%m.%Y} по {period.end:%d.%m.%Y}.',
            code='purchase_outside_period',
        )


def validate_photo(uploaded, max_bytes: int) -> str:
    from PIL import Image

    if uploaded.size > max_bytes:
        raise ValidationError(
            f'Файл больше {max_bytes // (1024 * 1024)} МБ.',
            code='photo_too_large',
        )
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as image:
            image_format = image.format
            image.verify()
    except Exception as e:
        raise ValidationError(
            'Файл повреждён или не является изображением.',
            code='photo_invalid',
        ) from e
    finally:
        uploaded.seek(0)
    if image_format not in PHOTO_FORMATS:
        raise ValidationError(
            'Поддерживаются только JPEG, PNG и WEBP.',
            code='photo_bad_format',
        )
    return {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[image_format]
