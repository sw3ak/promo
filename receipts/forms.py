import datetime

from django import forms
from django.conf import settings

from receipts import models
from receipts import qr
from receipts import services
from receipts import validators

PURCHASED_AT_FORMATS = (
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y %H:%M:%S',
)
_QR_FIELDS = ('fn', 'fd', 'fp', 'purchased_at', 'amount')


class ReceiptForm(forms.Form):
    qr_raw = forms.CharField(
        label='Строка из QR-кода', required=False, max_length=512
    )
    fn = forms.CharField(label='ФН', max_length=32)
    fd = forms.CharField(label='Номер чека (ФД)', max_length=32)
    fp = forms.CharField(label='ФП', max_length=32)
    purchased_at = forms.DateTimeField(
        label='Дата покупки',
        input_formats=PURCHASED_AT_FORMATS,
        error_messages={'invalid': 'Введите дату и время покупки.'},
    )
    amount = forms.CharField(label='Сумма', max_length=32)
    photo = forms.FileField(label='Фото чека', required=False)

    def __init__(self, data=None, files=None, **kwargs):
        self._qr_error = None
        if data is not None and (data.get('qr_raw') or '').strip():
            data = self._fill_from_qr(data.copy())
        super().__init__(data, files, **kwargs)

    def _fill_from_qr(self, data):
        try:
            parsed = qr.parse(data['qr_raw'])
        except qr.QrParseError as e:
            self._qr_error = str(e)
            return data
        values = {
            'fn': parsed.fn,
            'fd': parsed.fd,
            'fp': parsed.fp,
            'purchased_at': parsed.purchased_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'amount': parsed.amount,
        }
        for name in _QR_FIELDS:
            if not (data.get(name) or '').strip():
                data[name] = values[name]
        return data

    def clean_qr_raw(self) -> str:
        if self._qr_error:
            raise forms.ValidationError(self._qr_error, code='invalid_qr')
        return self.cleaned_data['qr_raw']

    def clean_fn(self) -> str:
        return validators.clean_fn(self.cleaned_data['fn'])

    def clean_fd(self) -> int:
        return validators.clean_fiscal_int(self.cleaned_data['fd'], 'ФД')

    def clean_fp(self) -> int:
        return validators.clean_fiscal_int(self.cleaned_data['fp'], 'ФП')

    def clean_purchased_at(self) -> datetime.datetime:
        value = self.cleaned_data['purchased_at']
        validators.validate_purchased_at(value)
        return value

    def clean_amount(self):
        amount = validators.parse_amount(self.cleaned_data['amount'])
        validators.validate_min_amount(amount)
        return amount

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return None
        extension = validators.validate_photo(
            photo, settings.RECEIPT_PHOTO_MAX_BYTES
        )
        photo.name = 'receipt' + extension
        return photo

    def to_input(self) -> services.ReceiptInput:
        data = self.cleaned_data
        return services.ReceiptInput(
            fn=data['fn'],
            fd=data['fd'],
            fp=data['fp'],
            purchased_at=data['purchased_at'],
            amount=data['amount'],
            photo=data.get('photo'),
        )


class ModerationForm(forms.ModelForm):
    class Meta:
        model = models.Receipt
        fields = ['status', 'rejection_reason']

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('status')
        reason = (cleaned.get('rejection_reason') or '').strip()
        if status == models.Receipt.Status.REJECTED and not reason:
            self.add_error(
                'rejection_reason', 'Укажите причину отказа для участника.'
            )
        cleaned['rejection_reason'] = reason
        return cleaned
