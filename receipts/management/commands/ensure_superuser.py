import os

from django.contrib import auth
from django.core.management import base


class Command(base.BaseCommand):
    help = 'Creates a superuser from DJANGO_SUPERUSER_* variables if missing.'

    def handle(self, *args, **options) -> None:
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        if not username or not password:
            self.stdout.write('DJANGO_SUPERUSER_* not set, skipping.')
            return
        users = auth.get_user_model().objects
        if users.filter(username=username).exists():
            self.stdout.write(f'Superuser {username!r} already exists.')
            return
        users.create_superuser(
            username=username, email=email, password=password
        )
        self.stdout.write(
            self.style.SUCCESS(f'Superuser {username!r} created.')
        )
