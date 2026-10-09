import datetime
import decimal
import typing
import urllib.parse

_REQUIRED_KEYS = ('t', 's', 'fn', 'i', 'fp')
_TIME_FORMATS = {15: '%Y%m%dT%H%M%S', 13: '%Y%m%dT%H%M'}


class QrParseError(ValueError):
    pass


class QrData(typing.NamedTuple):
    fn: str
    fd: str
    fp: str
    purchased_at: datetime.datetime
    amount: str


def parse(raw: str) -> QrData:
    text = (raw or '').strip().lstrip('?')
    params = {
        key.lower(): values[0].strip()
        for key, values in urllib.parse.parse_qs(text).items()
    }
    missing = [key for key in _REQUIRED_KEYS if not params.get(key)]
    if missing:
        raise QrParseError(
            'В строке QR-кода нет параметров: ' + ', '.join(missing) + '.'
        )
    purchased_at = _parse_time(params['t'])
    try:
        amount = decimal.Decimal(params['s'])
    except decimal.InvalidOperation as e:
        raise QrParseError('Неверная сумма в QR-коде.') from e
    return QrData(
        fn=params['fn'],
        fd=params['i'],
        fp=params['fp'],
        purchased_at=purchased_at,
        amount=f'{amount:.2f}',
    )


def _parse_time(value: str) -> datetime.datetime:
    time_format = _TIME_FORMATS.get(len(value))
    try:
        if time_format and value.isascii():
            return datetime.datetime.strptime(value, time_format)
    except ValueError:
        pass
    raise QrParseError('Неверная дата в QR-коде.')
