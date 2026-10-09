import django.db.models.deletion
import django.utils.timezone
import receipts.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Receipt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("fn", models.CharField(max_length=16, verbose_name="ФН")),
                ("fd", models.PositiveBigIntegerField(verbose_name="ФД (номер чека)")),
                ("fp", models.PositiveBigIntegerField(verbose_name="ФП")),
                (
                    "purchased_at",
                    models.DateTimeField(
                        help_text="Время, напечатанное на чеке (местное время кассы).",
                        verbose_name="дата и время покупки",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=10, verbose_name="сумма, ₽"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "На проверке"),
                            ("accepted", "Принят"),
                            ("rejected", "Отклонён"),
                        ],
                        default="pending",
                        max_length=16,
                        verbose_name="статус",
                    ),
                ),
                (
                    "rejection_reason",
                    models.TextField(blank=True, verbose_name="причина отказа"),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True,
                        upload_to=receipts.models.receipt_photo_path,
                        verbose_name="фото чека",
                    ),
                ),
                (
                    "submissions",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Сколько раз участник отправлял чек (с учётом повторных).",
                        verbose_name="отправок",
                    ),
                ),
                (
                    "registered_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="Время последней отправки чека участником.",
                        verbose_name="дата регистрации",
                    ),
                ),
                (
                    "moderated_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="дата модерации"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="создан"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="изменён"),
                ),
                (
                    "moderated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="модератор",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="receipts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="участник",
                    ),
                ),
            ],
            options={
                "verbose_name": "чек",
                "verbose_name_plural": "чеки",
                "ordering": ["-registered_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ReceiptStatusLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("pending", "На проверке"),
                            ("accepted", "Принят"),
                            ("rejected", "Отклонён"),
                        ],
                        max_length=16,
                        verbose_name="было",
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("pending", "На проверке"),
                            ("accepted", "Принят"),
                            ("rejected", "Отклонён"),
                        ],
                        max_length=16,
                        verbose_name="стало",
                    ),
                ),
                ("reason", models.TextField(blank=True, verbose_name="причина")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="когда"),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="кем изменён",
                    ),
                ),
                (
                    "receipt",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_log",
                        to="receipts.receipt",
                        verbose_name="чек",
                    ),
                ),
            ],
            options={
                "verbose_name": "изменение статуса",
                "verbose_name_plural": "история статусов",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="receipt",
            index=models.Index(
                fields=["user", "-registered_at", "-id"],
                name="receipt_user_registered_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="receipt",
            index=models.Index(
                condition=models.Q(("status", "pending")),
                fields=["registered_at"],
                name="receipt_pending_queue_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="receipt",
            index=models.Index(
                fields=["status", "-registered_at"],
                name="receipt_status_registered_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.UniqueConstraint(
                fields=("fn", "fd", "fp"),
                name="receipt_unique_fiscal_triple",
                violation_error_message="Этот чек уже зарегистрирован.",
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(
                condition=models.Q(("fn__regex", "^[0-9]{16}$")),
                name="receipt_fn_16_digits",
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(
                condition=models.Q(("fd__gte", 1), ("fd__lte", 4294967295)),
                name="receipt_fd_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(
                condition=models.Q(("fp__gte", 1), ("fp__lte", 4294967295)),
                name="receipt_fp_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gt", 0)), name="receipt_amount_positive"
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(
                condition=models.Q(("status__in", ["pending", "accepted", "rejected"])),
                name="receipt_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("status", "rejected"), _negated=True),
                    ("rejection_reason__regex", "\\S"),
                    _connector="OR",
                ),
                name="receipt_rejection_has_reason",
            ),
        ),
        migrations.AddIndex(
            model_name="receiptstatuslog",
            index=models.Index(
                fields=["receipt", "created_at"], name="receipt_log_receipt_idx"
            ),
        ),
    ]
