# api/forms.py

from django import forms
from .models import UmUserInformation
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), label='密码')
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label='确认密码')

    class Meta:
        model = UmUserInformation
        fields = [
            'user_email',
            'user_password',
            'user_name',
            'user_phone',
            'position',
            'department',
            # 添加其他需要的字段
        ]
        widgets = {
            'user_password': forms.PasswordInput(),
        }

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise ValidationError("密码不匹配。")
        return confirm_password

    def save(self, commit=True):
        user = super().save(commit=False)
        # 使用 Django 的 make_password 对密码进行哈希处理
        user.user_password = make_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    user_email = forms.EmailField(label='邮箱')
    password = forms.CharField(widget=forms.PasswordInput(), label='密码')
