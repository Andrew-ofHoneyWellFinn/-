from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # 入力された文字が「ユーザー名」または「メールアドレス」に一致するユーザーを探す（大文字・小文字を区別しない）
            user = User.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).first()
        except User.DoesNotExist:
            return None

        # ユーザーが見つかり、かつパスワードが合っていればログイン許可
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None