from django import http
from django import shortcuts


def home(request: http.HttpRequest) -> http.HttpResponse:
    if request.user.is_authenticated:
        return shortcuts.redirect('receipts:cabinet')
    return shortcuts.redirect('login')


def rules(request: http.HttpRequest) -> http.HttpResponse:
    return shortcuts.render(request, 'core/rules.html')
