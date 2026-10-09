from django import urls
from django.contrib.auth import decorators

from accounts import views

urlpatterns = [
    urls.path('signup/', views.signup, name='signup'),
    urls.path(
        'profile/',
        decorators.login_required(views.profile),
        name='profile',
    ),
]
