import datetime
import decimal

from django import test
from django.core import exceptions

from receipts import validators
from receipts.tests import factories

NOW = datetime.datetime(2025, 6, 15, 12, 0, tzinfo=datetime.UTC)


class FnTest(test.SimpleTestCase):
    def test_accepts_16_digits_and_strips_spaces(self):
        self.assertEqual(
            validators.clean_fn(' 9289 0001 0012 3456 '), '9289000100123456'
        )

    def test_rejects_wrong_length_and_letters(self):
        for value in ('123', '92890001001234567', '92890001001234ab', ''):
            with self.subTest(value=value):
                with self.assertRaises(exceptions.ValidationError):
                    validators.clean_fn(value)


class FiscalIntTest(test.SimpleTestCase):
    def test_normalizes_leading_zeros(self):
        self.assertEqual(validators.clean_fiscal_int('000123', 'ФД'), 123)

    def test_bounds(self):
        self.assertEqual(
            validators.clean_fiscal_int('4294967295', 'ФП'), 4294967295
        )
        for value in ('0', '4294967296', '12345678901', '12a', '-5', ''):
            with self.subTest(value=value):
                with self.assertRaises(exceptions.ValidationError):
                    validators.clean_fiscal_int(value, 'ФП')


class AmountTest(test.SimpleTestCase):
    def test_parses_common_formats(self):
        cases = {
            '1500': '1500.00',
            '1 500,5': '1500.50',
            '1500.50': '1500.50',
            '1 000 ₽': '1000.00',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(
                    validators.parse_amount(raw), decimal.Decimal(expected)
                )

    def test_rejects_bad_formats(self):
        for raw in ('abc', '1500.555', '-1000', '1e5', '', '100000000'):
            with self.subTest(raw=raw):
                with self.assertRaises(exceptions.ValidationError):
                    validators.parse_amount(raw)

    def test_minimum_is_inclusive(self):
        with factories.promo_settings():
            validators.validate_min_amount(decimal.Decimal('1000.00'))
            with self.assertRaises(exceptions.ValidationError) as ctx:
                validators.validate_min_amount(decimal.Decimal('999.99'))
        self.assertEqual(ctx.exception.code, 'amount_too_small')
        self.assertIn('1 000 ₽', ctx.exception.messages[0])


class PurchasedAtTest(test.SimpleTestCase):
    def setUp(self):
        self.enterContext(factories.promo_settings())

    def assert_valid(self, *args):
        validators.validate_purchased_at(factories.local(*args), now=NOW)

    def assert_code(self, code, *args):
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validators.validate_purchased_at(factories.local(*args), now=NOW)
        self.assertEqual(ctx.exception.code, code)

    def test_period_bounds_are_inclusive_by_calendar_date(self):
        self.assert_valid(2025, 3, 1, 0, 0)
        self.assert_valid(2025, 5, 31, 23, 59)

    def test_outside_period(self):
        self.assert_code('purchase_outside_period', 2025, 2, 28, 23, 59)
        self.assert_code('purchase_outside_period', 2025, 6, 1, 0, 0)

    def test_future_purchase(self):
        now = datetime.datetime(2025, 4, 10, 12, 0, tzinfo=datetime.UTC)
        validators.validate_purchased_at(
            datetime.datetime(2025, 4, 11, 2, 0), now=now
        )
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validators.validate_purchased_at(
                datetime.datetime(2025, 4, 11, 2, 1), now=now
            )
        self.assertEqual(ctx.exception.code, 'purchase_in_future')

    def test_wall_clock_is_independent_of_utc_offset(self):
        self.assert_valid(2025, 5, 31, 23, 30)
