from django.utils import timezone

from receipts import models
from receipts import validators


def receipt_to_dict(receipt: models.Receipt) -> dict:
    return {
        'id': receipt.pk,
        'fn': receipt.fn,
        'fd': receipt.fd,
        'fp': receipt.fp,
        'purchased_at': validators.wall_clock(receipt.purchased_at).isoformat(
            timespec='minutes'
        ),
        'amount': f'{receipt.amount:.2f}',
        'status': receipt.status,
        'status_display': receipt.get_status_display(),
        'rejection_reason': receipt.rejection_reason,
        'info': receipt.info_text,
        'has_photo': bool(receipt.photo),
        'photo_url': receipt.photo_url,
        'registered_at': timezone.localtime(receipt.registered_at).isoformat(),
        'updated_at': timezone.localtime(receipt.updated_at).isoformat(),
    }
