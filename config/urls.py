from django import urls
from django.contrib import admin

from core import views as core_views

admin.site.site_header = 'Чек - модерация'
admin.site.site_title = 'Чек'
admin.site.index_title = 'Модерация чеков'

urlpatterns = [
    urls.path('', core_views.home, name='home'),
    urls.path('rules/', core_views.rules, name='rules'),
    urls.path('accounts/', urls.include('accounts.urls')),
    urls.path('accounts/', urls.include('django.contrib.auth.urls')),
    urls.path('api/', urls.include('receipts.api_urls')),
    urls.path('admin/', admin.site.urls),
    urls.path('', urls.include('receipts.urls')),
]
