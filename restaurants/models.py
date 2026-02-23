from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)

    # 지도/좌표는 나중에
    # lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    # lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    thumbnail = models.ImageField(upload_to="restaurants/thumbs/", blank=True, null=True)

    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
