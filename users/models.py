from django.db import models
from django.contrib.auth.models import User


# 이메일 인증 토큰
class EmailVerificationToken(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE)
    token      = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - 이메일 인증 토큰"


# 비밀번호 재설정 토큰
class PasswordResetToken(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    token      = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - 비밀번호 재설정 토큰"