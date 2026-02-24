from django.db import models
from django.conf import settings
from restaurants.models import Restaurant  # 식당 모델이 정의된 곳을 임포트

class Favorite(models.Model):
    # 1. 누가 즐겨찾기 했는가 (User 모델과 연결)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    
    # 2. 어떤 식당을 즐겨찾기 했는가 (Restaurant 모델과 연결)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='favorited_by')
    
    # 3. 언제 즐겨찾기 했는가 (선택 사항)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 한 사용자가 같은 식당을 중복해서 즐겨찾기 할 수 없도록 설정
        unique_together = ('user', 'restaurant')

    def __str__(self):
        return f"{self.user.username} - {self.restaurant.name}"