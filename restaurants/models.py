import requests
from django.db import models

# 1. Category 모델이 반드시 Restaurant보다 위에 있어야 합니다!
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# 2. Restaurant 모델
class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)

    # 좌표 필드 (네이버 API가 소수점 자리가 길어서 넉넉하게 잡았습니다)
    lat = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=13, decimal_places=8, null=True, blank=True)

    thumbnail = models.ImageField(upload_to="restaurants/thumbs/", blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 주소가 있고 좌표가 없을 때만 API 호출
        if self.address and not (self.lat and self.lng):
            self.get_coords_from_naver()
        super().save(*args, **kwargs)

    def get_coords_from_naver(self):
        client_id = "3z7t86u9wa"
        client_secret = "IS2ws9rljq7339ajeMpbkeKMtCe3cxwVEP4jN7V2"
        endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        
        headers = {
            "x-ncp-apigw-api-key-id": client_id,
            "x-ncp-apigw-api-key": client_secret,
        }
        params = {"query": self.address}
        
        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=5)
            data = response.json()
            if data.get('addresses'):
                self.lng = data['addresses'][0]['x']
                self.lat = data['addresses'][0]['y']
        except Exception as e:
            print(f"좌표 변환 중 오류: {e}")

    def __str__(self):
        return self.name