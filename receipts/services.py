import datetime
import decimal
import logging
import typing

from django.conf import settings
from django.core.files import uploadedfile
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from receipts import models

logger = logging.getLogger(__name__)

Receipt = models.Receipt
Status = models.Receipt.Status


class RegistrationError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class ModerationError(ValueError):
    pass


class ReceiptInput(typing.NamedTuple):
    fn: str
    fd: int
    fp: int
    purchased_at: datetime.datetime
    amount: decimal.Decimal
    photo: uploadedfile.UploadedFile | None = None


class RegistrationResult(typing.NamedTuple):
    receipt: Receipt
    resubmitted: bool


def register_receipt(user, data: ReceiptInput) -> RegistrationResult:
    with transaction.atomic():
        existing = (
            Receipt.objects.select_for_update()
            .filter(fn=data.fn, fd=data.fd, fp=data.fp)
            .first()
        )
        if existing is not None:
            return _resubmit(existing, user, data)
        receipt = Receipt(
            user=user,
            fn=data.fn,
            fd=data.fd,
            fp=data.fp,
            purchased_at=data.purchased_at,
            amount=data.amount,
            status=Status.PENDING,
        )
        if data.photo:
            receipt.photo = data.photo
        try:
            with transaction.atomic():
                receipt.save()
        except IntegrityError as e:
            if receipt.photo:
                receipt.photo.delete(save=False)
            raise RegistrationError(
                'Этот чек уже зарегистрирован.', code='duplicate'
            ) from e
        _log(receipt, '', Status.PENDING, '', user)
    logger.info('Receipt %s registered by user %s', receipt.pk, user.pk)
    return RegistrationResult(receipt=receipt, resubmitted=False)


def _resubmit(receipt: Receipt, user, data: ReceiptInput) -> RegistrationResult:
    if receipt.user_id != user.pk:
        raise RegistrationError(
            'Этот чек уже зарегистрирован другим участником акции.',
            code='duplicate_other_user',
        )
    if receipt.status != Status.REJECTED:
        raise RegistrationError(
            'Вы уже зарегистрировали этот чек. Его статус можно посмотреть '
            'в личном кабинете.',
            code='duplicate_own',
        )
    if receipt.submissions > settings.RECEIPT_MAX_RESUBMISSIONS:
        raise RegistrationError(
            'Чек отклонён, лимит повторных отправок исчерпан. Если вы не '
            'согласны с решением, напишите в поддержку.',
            code='resubmission_limit',
        )
    old_photo = receipt.photo.name if receipt.photo else ''
    receipt.purchased_at = data.purchased_at
    receipt.amount = data.amount
    receipt.status = Status.PENDING
    receipt.rejection_reason = ''
    receipt.submissions += 1
    receipt.registered_at = timezone.now()
    receipt.moderated_at = None
    receipt.moderated_by = None
    if data.photo:
        receipt.photo = data.photo
    receipt.save()
    if data.photo and old_photo:
        storage = receipt.photo.storage
        transaction.on_commit(lambda: storage.delete(old_photo))
    _log(receipt, Status.REJECTED, Status.PENDING, 'Повторная отправка', user)
    logger.info('Receipt %s re-sent by user %s', receipt.pk, user.pk)
    return RegistrationResult(receipt=receipt, resubmitted=True)


def change_status(
    receipt_id: int, *, status: str, reason: str = '', moderator
) -> bool:
    if status not in Status.values:
        raise ModerationError(f'Неизвестный статус: {status}.')
    reason = (reason or '').strip()
    if status == Status.REJECTED and not reason:
        raise ModerationError('Укажите причину отказа.')
    if status != Status.REJECTED:
        reason = ''
    with transaction.atomic():
        receipt = Receipt.objects.select_for_update().get(pk=receipt_id)
        if receipt.status == status and receipt.rejection_reason == reason:
            return False
        previous = receipt.status
        receipt.status = status
        receipt.rejection_reason = reason
        receipt.moderated_at = timezone.now()
        receipt.moderated_by = moderator
        receipt.save(
            update_fields=[
                'status',
                'rejection_reason',
                'moderated_at',
                'moderated_by',
                'updated_at',
            ]
        )
        _log(receipt, previous, status, reason, moderator)
    logger.info(
        'Receipt %s: %s -> %s by %s',
        receipt.pk,
        previous,
        status,
        moderator.pk,
    )
    return True


def _log(receipt, from_status, to_status, reason, changed_by) -> None:
    models.ReceiptStatusLog.objects.create(
        receipt=receipt,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        changed_by=changed_by,
    )
