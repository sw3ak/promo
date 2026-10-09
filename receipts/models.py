import pathlib
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

FISCAL_INT_MAX = 4_294_967_295
FN_LENGTH = 16


def receipt_photo_path(unused_instance: 'Receipt', filename: str) -> str:
    extension = pathlib.Path(filename).suffix.lower()
    today = timezone.now()
    return f'receipts/{today:%Y/%m/%d}/{uuid.uuid4().hex}{extension}'


class ReceiptStatus(models.TextChoices):
    PENDING = 'pending', 'На проверке'
    ACCEPTED = 'accepted', 'Принят'
    REJECTED = 'rejected', 'Отклонён'


class Receipt(models.Model):
    Status = ReceiptStatus

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='receipts',
        verbose_name='участник',
        db_index=False,
    )
    fn = models.CharField('ФН', max_length=FN_LENGTH)
    fd = models.PositiveBigIntegerField('ФД (номер чека)')
    fp = models.PositiveBigIntegerField('ФП')
    purchased_at = models.DateTimeField(
        'дата и время покупки',
        help_text='Время, напечатанное на чеке (местное время кассы).',
    )
    amount = models.DecimalField('сумма, ₽', max_digits=10, decimal_places=2)
    status = models.CharField(
        'статус',
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField('причина отказа', blank=True)
    photo = models.ImageField(
        'фото чека', upload_to=receipt_photo_path, blank=True
    )
    submissions = models.PositiveSmallIntegerField(
        'отправок',
        default=1,
        help_text='Сколько раз участник отправлял чек (с учётом повторных).',
    )
    registered_at = models.DateTimeField(
        'дата регистрации',
        default=timezone.now,
        help_text='Время последней отправки чека участником.',
    )
    moderated_at = models.DateTimeField('дата модерации', null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='модератор',
    )
    created_at = models.DateTimeField('создан', auto_now_add=True)
    updated_at = models.DateTimeField('изменён', auto_now=True)

    class Meta:
        verbose_name = 'чек'
        verbose_name_plural = 'чеки'
        ordering = ['-registered_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['fn', 'fd', 'fp'],
                name='receipt_unique_fiscal_triple',
                violation_error_message='Этот чек уже зарегистрирован.',
            ),
            models.CheckConstraint(
                condition=models.Q(fn__regex=r'^[0-9]{16}$'),
                name='receipt_fn_16_digits',
            ),
            models.CheckConstraint(
                condition=models.Q(fd__gte=1, fd__lte=FISCAL_INT_MAX),
                name='receipt_fd_range',
            ),
            models.CheckConstraint(
                condition=models.Q(fp__gte=1, fp__lte=FISCAL_INT_MAX),
                name='receipt_fp_range',
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='receipt_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ReceiptStatus.values),
                name='receipt_status_valid',
            ),
            models.CheckConstraint(
                condition=~models.Q(status=ReceiptStatus.REJECTED)
                | models.Q(rejection_reason__regex=r'\S'),
                name='receipt_rejection_has_reason',
            ),
        ]
        indexes = [
            models.Index(
                fields=['user', '-registered_at', '-id'],
                name='receipt_user_registered_idx',
            ),
            models.Index(
                fields=['registered_at'],
                condition=models.Q(status=ReceiptStatus.PENDING),
                name='receipt_pending_queue_idx',
            ),
            models.Index(
                fields=['status', '-registered_at'],
                name='receipt_status_registered_idx',
            ),
        ]

    def __str__(self) -> str:
        return f'Чек ФН {self.fn} / ФД {self.fd} / ФП {self.fp}'

    @property
    def info_text(self) -> str:
        if self.status == self.Status.REJECTED:
            return self.rejection_reason
        if self.status == self.Status.ACCEPTED:
            return 'Чек принят и участвует в розыгрыше'
        return 'Чек на проверке'

    @property
    def photo_url(self) -> str | None:
        if not self.photo:
            return None
        return reverse('receipts:photo', args=[self.pk])


class ReceiptStatusLog(models.Model):
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='status_log',
        verbose_name='чек',
        db_index=False,
    )
    from_status = models.CharField(
        'было', max_length=16, choices=ReceiptStatus.choices, blank=True
    )
    to_status = models.CharField(
        'стало', max_length=16, choices=ReceiptStatus.choices
    )
    reason = models.TextField('причина', blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='кем изменён',
    )
    created_at = models.DateTimeField('когда', auto_now_add=True)

    class Meta:
        verbose_name = 'изменение статуса'
        verbose_name_plural = 'история статусов'
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(
                fields=['receipt', 'created_at'],
                name='receipt_log_receipt_idx',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.from_status or "—"} → {self.to_status}'
