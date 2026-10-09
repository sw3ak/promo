import decimal
import shutil
import tempfile
from unittest import mock

from django import test
from django.db import IntegrityError
from django.db import transaction

from receipts import models
from receipts import services
from receipts.tests import factories

Status = models.Receipt.Status


def receipt_input(**overrides) -> services.ReceiptInput:
    values = {
        'fn': '9289000100123456',
        'fd': 12345,
        'fp': 987654321,
        'purchased_at': factories.local(2025, 4, 10, 14, 30),
        'amount': decimal.Decimal('1500.00'),
    }
    values.update(overrides)
    return services.ReceiptInput(**values)


class RegisterReceiptTest(test.TestCase):
    def setUp(self):
        self.enterContext(factories.promo_settings())
        self.user = factories.make_user()

    def test_new_receipt_is_pending_and_logged(self):
        result = services.register_receipt(self.user, receipt_input())
        receipt = result.receipt
        self.assertFalse(result.resubmitted)
        self.assertEqual(receipt.status, Status.PENDING)
        self.assertEqual(receipt.user, self.user)
        log = receipt.status_log.get()
        self.assertEqual((log.from_status, log.to_status), ('', 'pending'))

    def test_duplicate_of_own_pending_receipt(self):
        services.register_receipt(self.user, receipt_input())
        with self.assertRaises(services.RegistrationError) as ctx:
            services.register_receipt(self.user, receipt_input())
        self.assertEqual(ctx.exception.code, 'duplicate_own')
        self.assertEqual(models.Receipt.objects.count(), 1)

    def test_duplicate_of_other_users_receipt(self):
        services.register_receipt(self.user, receipt_input())
        with self.assertRaises(services.RegistrationError) as ctx:
            services.register_receipt(factories.make_user(), receipt_input())
        self.assertEqual(ctx.exception.code, 'duplicate_other_user')

    def test_triple_identifies_receipt_regardless_of_other_fields(self):
        services.register_receipt(self.user, receipt_input())
        with self.assertRaises(services.RegistrationError):
            services.register_receipt(
                self.user, receipt_input(amount=decimal.Decimal('5000'))
            )

    def test_different_fp_is_a_different_receipt(self):
        services.register_receipt(self.user, receipt_input())
        services.register_receipt(self.user, receipt_input(fp=1))
        self.assertEqual(models.Receipt.objects.count(), 2)

    def test_rejected_receipt_can_be_resent_by_owner(self):
        receipt = services.register_receipt(self.user, receipt_input()).receipt
        services.change_status(
            receipt.pk,
            status=Status.REJECTED,
            reason='Нечитаемое фото',
            moderator=factories.make_moderator(),
        )
        result = services.register_receipt(
            self.user, receipt_input(amount=decimal.Decimal('2000'))
        )
        receipt.refresh_from_db()
        self.assertTrue(result.resubmitted)
        self.assertEqual(result.receipt.pk, receipt.pk)
        self.assertEqual(receipt.status, Status.PENDING)
        self.assertEqual(receipt.rejection_reason, '')
        self.assertEqual(receipt.amount, decimal.Decimal('2000'))
        self.assertEqual(receipt.submissions, 2)
        self.assertIsNone(receipt.moderated_by)
        self.assertEqual(receipt.status_log.count(), 3)

    def test_resubmission_limit(self):
        moderator = factories.make_moderator()
        receipt = services.register_receipt(self.user, receipt_input()).receipt
        for _ in range(2):
            services.change_status(
                receipt.pk,
                status=Status.REJECTED,
                reason='Нет',
                moderator=moderator,
            )
            services.register_receipt(self.user, receipt_input())
        services.change_status(
            receipt.pk,
            status=Status.REJECTED,
            reason='Нет',
            moderator=moderator,
        )
        with self.assertRaises(services.RegistrationError) as ctx:
            services.register_receipt(self.user, receipt_input())
        self.assertEqual(ctx.exception.code, 'resubmission_limit')

    def test_other_user_cannot_resend_rejected_receipt(self):
        receipt = services.register_receipt(self.user, receipt_input()).receipt
        services.change_status(
            receipt.pk,
            status=Status.REJECTED,
            reason='Нет',
            moderator=factories.make_moderator(),
        )
        with self.assertRaises(services.RegistrationError) as ctx:
            services.register_receipt(factories.make_user(), receipt_input())
        self.assertEqual(ctx.exception.code, 'duplicate_other_user')

    def test_concurrent_insert_is_reported_as_duplicate(self):
        with mock.patch.object(
            models.Receipt, 'save', side_effect=IntegrityError('dup')
        ):
            with self.assertRaises(services.RegistrationError) as ctx:
                services.register_receipt(self.user, receipt_input())
        self.assertEqual(ctx.exception.code, 'duplicate')

    def test_database_rejects_duplicate_triple(self):
        factories.make_receipt(self.user, fn='9289000100000001', fd=1, fp=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            factories.make_receipt(self.user, fn='9289000100000001', fd=1, fp=1)


class DatabaseConstraintsTest(test.TestCase):
    def setUp(self):
        self.user = factories.make_user()

    def assert_rejected_by_db(self, **fields):
        with self.assertRaises(IntegrityError), transaction.atomic():
            factories.make_receipt(self.user, **fields)

    def test_constraints(self):
        self.assert_rejected_by_db(fn='123')
        self.assert_rejected_by_db(fd=0)
        self.assert_rejected_by_db(fp=4_294_967_296)
        self.assert_rejected_by_db(amount=decimal.Decimal('0'))
        self.assert_rejected_by_db(status='unknown')
        self.assert_rejected_by_db(status='rejected', rejection_reason='  ')


class ChangeStatusTest(test.TestCase):
    def setUp(self):
        self.receipt = factories.make_receipt(factories.make_user())
        self.moderator = factories.make_moderator()

    def test_reject_requires_reason(self):
        with self.assertRaises(services.ModerationError):
            services.change_status(
                self.receipt.pk,
                status=Status.REJECTED,
                reason=' ',
                moderator=self.moderator,
            )

    def test_unknown_status(self):
        with self.assertRaises(services.ModerationError):
            services.change_status(
                self.receipt.pk, status='won', moderator=self.moderator
            )

    def test_accept_clears_reason_and_stamps_moderator(self):
        services.change_status(
            self.receipt.pk,
            status=Status.REJECTED,
            reason='Причина',
            moderator=self.moderator,
        )
        changed = services.change_status(
            self.receipt.pk,
            status=Status.ACCEPTED,
            reason='ignored',
            moderator=self.moderator,
        )
        self.receipt.refresh_from_db()
        self.assertTrue(changed)
        self.assertEqual(self.receipt.status, Status.ACCEPTED)
        self.assertEqual(self.receipt.rejection_reason, '')
        self.assertEqual(self.receipt.moderated_by, self.moderator)
        self.assertIsNotNone(self.receipt.moderated_at)

    def test_same_status_is_noop(self):
        changed = services.change_status(
            self.receipt.pk, status=Status.PENDING, moderator=self.moderator
        )
        self.assertFalse(changed)
        self.assertFalse(self.receipt.status_log.exists())


class PhotoReplacementTest(test.TestCase):
    def setUp(self):
        self.enterContext(factories.promo_settings())
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = test.override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)

    def test_resend_with_new_photo_deletes_old_file(self):
        user = factories.make_user()
        receipt = services.register_receipt(
            user, receipt_input(photo=factories.image_file())
        ).receipt
        old_name = receipt.photo.name
        storage = receipt.photo.storage
        self.assertTrue(storage.exists(old_name))
        services.change_status(
            receipt.pk,
            status=Status.REJECTED,
            reason='Фото нечитаемо',
            moderator=factories.make_moderator(),
        )
        with self.captureOnCommitCallbacks(execute=True):
            services.register_receipt(
                user, receipt_input(photo=factories.image_file())
            )
        receipt.refresh_from_db()
        self.assertNotEqual(receipt.photo.name, old_name)
        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(receipt.photo.name))
