import requests
from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.name

class Restaurant(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="restaurants", null=True, blank=True)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    
    # 추가 운영 정보 필드
    hours = models.CharField(max_length=100, blank=True)
    closed_days = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    lat = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=13, decimal_places=8, null=True, blank=True)
    thumbnail = models.ImageField(upload_to="restaurants/thumbs/", blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 주소가 있고 좌표가 없을 때 자동 변환
        if self.address and not (self.lat and self.lng):
            self.get_coords_from_naver()
        super().save(*args, **kwargs)

    def get_coords_from_naver(self):
        client_id = "3z7t86u9wa"
        client_secret = "IS2ws9rljq7339ajeMpbkeKMtCe3cxwVEP4jN7V2"
        endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        headers = {"x-ncp-apigw-api-key-id": client_id, "x-ncp-apigw-api-key": client_secret}
        try:
            response = requests.get(endpoint, headers=headers, params={"query": self.address}, timeout=5)
            data = response.json()
            if data.get('addresses'):
                self.lng = data['addresses'][0]['x']
                self.lat = data['addresses'][0]['y']
        except Exception as e: print(f"좌표 변환 오류: {e}")

    def __str__(self): return self.name