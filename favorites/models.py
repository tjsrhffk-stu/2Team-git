from django.db import models
from django.contrib.auth.models import User
from restaurants.models import Restaurant

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "restaurant"], name="unique_favorite")
        ]

    def __str__(self):
        return f"{self.user.username} ♥ {self.restaurant.name}"
