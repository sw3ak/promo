from django.contrib import admin
from django.utils import html

from receipts import forms
from receipts import models
from receipts import services


@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    form = forms.ModerationForm
    list_display = (
        'id',
        'user',
        'fn',
        'fd',
        'fp',
        'purchased_at',
        'amount',
        'status',
        'registered_at',
    )
    list_filter = ('status',)
    search_fields = ('=fn', '=fd', '=fp', '^user__email', '^user__username')
    search_help_text = 'Поиск по ФН, ФД, ФП (точно) или началу email/логина.'
    list_select_related = ('user',)
    readonly_fields = (
        'user',
        'fn',
        'fd',
        'fp',
        'purchased_at',
        'amount',
        'photo_preview',
        'registered_at',
    )
    fields = readonly_fields + ('status', 'rejection_reason')

    def has_add_permission(self, request) -> bool:
        return False

    @admin.display(description='Фото')
    def photo_preview(self, obj: models.Receipt) -> str:
        if not obj.photo:
            return '—'
        return html.format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" alt="Фото чека" style="max-height:320px"></a>',
            obj.photo_url,
        )

    def save_model(self, request, obj, form, change) -> None:
        if change and form.has_changed():
            services.change_status(
                obj.pk,
                status=form.cleaned_data['status'],
                reason=form.cleaned_data['rejection_reason'],
                moderator=request.user,
            )
            obj.refresh_from_db()
