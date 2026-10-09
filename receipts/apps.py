from django import apps
from django.core import checks


class ReceiptsConfig(apps.AppConfig):
    name = 'receipts'
    verbose_name = 'Чеки'

    def ready(self) -> None:
        from receipts import checks as promo_checks

        checks.register(promo_checks.check_promo_settings)
