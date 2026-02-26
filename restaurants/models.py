import requests
from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Restaurant(models.Model):
    # [Owner 필드] feature 브랜치의 변경사항 반영
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurants",
        null=True,
        blank=True,
    )
    
    # [기본 정보] main 브랜치의 상세 필드들
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    
    # [운영 정보]
    hours = models.CharField(max_length=100, blank=True)
    closed_days = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    # [위치 및 메타 정보]
    lat = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    lng = models.DecimalField(max_digits=13, decimal_places=8, null=True, blank=True)
    thumbnail = models.ImageField(upload_to="restaurants/thumbs/", blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 주소가 있고 좌표가 없을 때 네이버 API를 통해 좌표 자동 변환
        if self.address and not (self.lat and self.lng):
            self.get_coords_from_naver()
        super().save(*args, **kwargs)

    def get_coords_from_naver(self):
        """네이버 지오코딩 API를 사용하여 주소를 좌표로 변환"""
        client_id = "3z7t86u9wa"
        client_secret = "IS2ws9rljq7339ajeMpbkeKMtCe3cxwVEP4jN7V2"
        endpoint = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
        headers = {
            "x-ncp-apigw-api-key-id": client_id, 
            "x-ncp-apigw-api-key": client_secret
        }
        
        try:
            response = requests.get(endpoint, headers=headers, params={"query": self.address}, timeout=5)
            data = response.json()
            if data.get('addresses'):
                # API 응답에서 경도(lng)와 위도(lat) 추출
                self.lng = data['addresses'][0]['x']
                self.lat = data['addresses'][0]['y']
        except Exception as e:
            print(f"좌표 변환 오류: {e}")

    def __str__(self):
        return self.name
    
    # 사진 다중 등록 준비
class RestaurantImage(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, 
        related_name='additional_images', # 이 이름으로 상세페이지에서 불러옵니다
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="restaurants/gallery/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.restaurant.name} - Image"