from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Accounts


class JWTAccountAuthentication(BaseAuthentication):
    """
    Đọc claim `account_id` được nhúng trong access token (LoginView tự set),
    thay vì dùng cơ chế user_id + Django User model mặc định của SimpleJWT.
    request.user sẽ là một instance của Accounts.
    """
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        raw_token = parts[1]
        try:
            validated_token = AccessToken(raw_token)
        except TokenError as e:
            raise AuthenticationFailed(str(e))

        account_id = validated_token.get("account_id")
        if account_id is None:
            raise AuthenticationFailed("Token không hợp lệ.")

        try:
            account = Accounts.objects.get(id=account_id, deleted_at__isnull=True)
        except Accounts.DoesNotExist:
            raise AuthenticationFailed("Tài khoản không tồn tại.")

        return (account, validated_token)