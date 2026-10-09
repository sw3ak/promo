from django import forms
from django.contrib import auth
from django.contrib.auth import forms as auth_forms


class SignUpForm(auth_forms.UserCreationForm):
    email = forms.EmailField(label='Email', required=True)

    class Meta(auth_forms.UserCreationForm.Meta):
        model = auth.get_user_model()
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_email(self) -> str:
        email = self.cleaned_data['email'].strip().lower()
        if auth.get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Этот email уже зарегистрирован.')
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = auth.get_user_model()
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self) -> str:
        email = self.cleaned_data['email'].strip().lower()
        users = auth.get_user_model().objects.filter(email__iexact=email)
        if email and users.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Этот email уже зарегистрирован.')
        return email
