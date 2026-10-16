from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label='メールアドレス',
        required=True,
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    # すでに登録されているメールアドレスを弾くチェック処理
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('このメールアドレスは既に登録されています。')
        return email