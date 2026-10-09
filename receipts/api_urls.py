from django import urls

from receipts import api

app_name = 'api'

urlpatterns = [
    urls.path('receipts/', api.receipt_list, name='receipts'),
]
