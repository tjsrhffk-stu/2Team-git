from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from restaurants.models import Restaurant

class Review(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5, db_index=True)  # 1~5, 별점 필터 인덱스
    content = models.TextField()
    image = models.ImageField(upload_to="reviews/photos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # 정렬 인덱스

    class Meta:
        ordering = ["-created_at"]
        unique_together = ('restaurant', 'author')  # 1인 1리뷰 제한 (DB 레벨)

    def __str__(self):
        return f"{self.restaurant.name} - {self.author.username} ({self.rating})"



class ReviewReply(models.Model):
    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name='reply'   # 템플릿에서 review.reply 로 접근
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.review.restaurant.name} 사장님 답글"


class ReviewLike(models.Model):
    """리뷰 좋아요"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user')

    def __str__(self):
        return f"{self.user} → {self.review}"


class ReviewReport(models.Model):
    """리뷰 신고"""
    REASON_CHOICES = [
        ('spam',  '스팸/광고'),
        ('bad',   '욕설/혐오'),
        ('false', '허위 정보'),
        ('other', '기타'),
    ]
    review   = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_reports')
    reason   = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'reporter')

    def __str__(self):
        return f"{self.reporter} 신고 → {self.review.pk}"
