from django import urls
from django.contrib.auth import decorators

from receipts import views

app_name = 'receipts'

urlpatterns = [
    urls.path(
        'cabinet/',
        decorators.login_required(views.cabinet),
        name='cabinet',
    ),
    urls.path(
        'receipts/new/',
        decorators.login_required(views.register),
        name='register',
    ),
    urls.path(
        'receipts/success/',
        decorators.login_required(views.success),
        name='success',
    ),
    urls.path(
        'receipts/<int:pk>/photo/',
        decorators.login_required(views.photo),
        name='photo',
    ),
]
