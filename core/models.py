from django.db import models
from django.conf import settings


class Notification(models.Model):
    """답글/알림"""
    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message    = models.CharField(max_length=200)
    url        = models.CharField(max_length=500, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"→{self.recipient}: {self.message}"


class FoodStory(models.Model):
    """홈 화면 푸드스토리 / 기사 카드"""
    title        = models.CharField(max_length=200)
    subtitle     = models.CharField(max_length=200, blank=True)
    thumbnail    = models.ImageField(upload_to='stories/', blank=True, null=True)
    external_url = models.URLField(blank=True, help_text="외부 기사 링크 (선택)")
    badge        = models.CharField(max_length=30, blank=True, help_text="예: HOT, NEW, 추천")
    is_published = models.BooleanField(default=True)
    order        = models.PositiveSmallIntegerField(default=0, help_text="숫자 낮을수록 먼저 표시")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title
