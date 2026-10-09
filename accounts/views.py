from django import http
from django import shortcuts
from django.contrib import auth
from django.contrib import messages

from accounts import forms


def signup(request: http.HttpRequest) -> http.HttpResponse:
    if request.user.is_authenticated:
        return shortcuts.redirect('receipts:cabinet')
    form = forms.SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        auth.login(request, user)
        return shortcuts.redirect('receipts:cabinet')
    return shortcuts.render(request, 'registration/signup.html', {'form': form})


def profile(request: http.HttpRequest) -> http.HttpResponse:
    form = forms.ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Профиль сохранён.')
        return shortcuts.redirect('profile')
    return shortcuts.render(request, 'accounts/profile.html', {'form': form})
