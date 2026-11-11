from django import forms
from django.core.validators import RegexValidator

from .models import Feedback, User

phone_validator = RegexValidator(r'^\+?[0-9\s()\-]{10,20}$', 'Введите корректный номер телефона')


class RegisterForm(forms.Form):
    username = forms.CharField(min_length=3, max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(required=False, validators=[phone_validator])
    password = forms.CharField(min_length=8, strip=False)
    password_confirm = forms.CharField(strip=False)
    terms = forms.BooleanField()
    privacy = forms.BooleanField()

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Этот email уже зарегистрирован')
        return email

    def clean(self):
        data = super().clean()
        if data.get('password') != data.get('password_confirm'):
            self.add_error('password_confirm', 'Пароли не совпадают')
        return data


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(strip=False)
    remember = forms.BooleanField(required=False)


class ProfileForm(forms.Form):
    name = forms.CharField(min_length=2, max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(required=False, validators=[phone_validator])

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Этот email уже занят')
        return email


class PasswordForm(forms.Form):
    old_password = forms.CharField(strip=False)
    new_password = forms.CharField(min_length=8, strip=False)
    confirm_password = forms.CharField(strip=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old = self.cleaned_data['old_password']
        if not self.user.check_password(old):
            raise forms.ValidationError('Неверный текущий пароль')
        return old

    def clean(self):
        data = super().clean()
        if data.get('new_password') != data.get('confirm_password'):
            self.add_error('confirm_password', 'Пароли не совпадают')
        return data


class FeedbackForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(required=False, validators=[phone_validator])
    subject = forms.ChoiceField(choices=Feedback.SUBJECTS)
    message = forms.CharField(min_length=10, max_length=2000)
    rating = forms.IntegerField(required=False, min_value=1, max_value=5)
    privacy = forms.BooleanField()