from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label='メールアドレス',
        required=True,
    )
    agreement = forms.BooleanField(
        label='利用規約とプライバシーポリシーに同意します',
        required=True,
        error_messages={'required': '利用規約とプライバシーポリシーへの同意が必要です。'},
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


class ContactForm(forms.Form):
    subject = forms.CharField(label='件名', max_length=100)
    message = forms.CharField(label='お問い合わせ内容', widget=forms.Textarea, max_length=2000)