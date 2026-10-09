import datetime
import decimal
import io
import itertools

from django.contrib import auth
from django.core.files import uploadedfile
from django.test import utils
from django.utils import timezone
from PIL import Image

from receipts import models

PROMO_SETTINGS = dict(
    PROMO_START_DATE=datetime.date(2025, 3, 1),
    PROMO_END_DATE=datetime.date(2025, 5, 31),
    PROMO_MIN_AMOUNT=decimal.Decimal('1000'),
    RECEIPT_MAX_RESUBMISSIONS=2,
    RECEIPT_PHOTO_MAX_BYTES=1024 * 1024,
    RECEIPT_SUBMIT_RATE_LIMIT=0,
)

_counter = itertools.count(1)


def promo_settings() -> utils.override_settings:
    return utils.override_settings(**PROMO_SETTINGS)


def make_user(username=None, **extra):
    username = username or f'user{next(_counter)}'
    return auth.get_user_model().objects.create_user(
        username=username,
        password='password',
        email=f'{username}@example.com',
        **extra,
    )


def make_moderator():
    return auth.get_user_model().objects.create_superuser(
        username=f'moderator{next(_counter)}',
        password='password',
        email=f'moderator{next(_counter)}@example.com',
    )


def local(*args) -> datetime.datetime:
    return timezone.make_aware(datetime.datetime(*args))


def make_receipt(user, **fields) -> models.Receipt:
    number = next(_counter)
    values = {
        'fn': f'{9289000100000000 + number}',
        'fd': number,
        'fp': 1_000_000 + number,
        'purchased_at': local(2025, 4, 10, 12, 0),
        'amount': decimal.Decimal('1500.00'),
    }
    values.update(fields)
    return models.Receipt.objects.create(user=user, **values)


def image_file(
    name='receipt.png', image_format='PNG', size=(20, 20)
) -> uploadedfile.SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new('RGB', size, 'white').save(buffer, format=image_format)
    content_type = {'PNG': 'image/png', 'JPEG': 'image/jpeg'}.get(
        image_format, 'application/octet-stream'
    )
    return uploadedfile.SimpleUploadedFile(
        name, buffer.getvalue(), content_type=content_type
    )
