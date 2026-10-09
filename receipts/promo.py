import datetime
import decimal
import typing

from django.conf import settings


class PromoPeriod(typing.NamedTuple):
    start: datetime.date
    end: datetime.date

    def contains(self, day: datetime.date) -> bool:
        return self.start <= day <= self.end


def get_period() -> PromoPeriod:
    return PromoPeriod(
        start=settings.PROMO_START_DATE, end=settings.PROMO_END_DATE
    )


def get_min_amount() -> decimal.Decimal:
    return settings.PROMO_MIN_AMOUNT
