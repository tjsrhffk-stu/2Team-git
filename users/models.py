from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    email_token = models.CharField(max_length=64, null=True, blank=True)
    email_token_created_at = models.DateTimeField(null=True, blank=True)

    reset_token = models.CharField(max_length=64, null=True, blank=True)
    reset_token_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"


class OwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_profile')

    # ✅ 기존 DB에 OwnerProfile이 있어도 마이그레이션 막히지 않게 null 허용
    # ✅ 가입 로직에서 business_number 입력을 '필수'로 강제함
    business_number = models.CharField(max_length=10, unique=True, null=True, blank=True)

    def __str__(self):
        return f"Owner<{self.user.username}> ({self.business_number})"


@receiver(post_save, sender=User)
def create_profiles(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)