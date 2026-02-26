from django.urls import path
from . import views

app_name = "restaurants"

urlpatterns = [
    # 1. 목록 및 검색
    path("", views.restaurant_list, name="list"),
    
    # 2. 음식점 등록 (중복 제거 및 이름 통일)
    path("create/", views.restaurant_create, name="create"),
    
    # 3. 지도 보기
    path("map/", views.restaurant_map, name="map"),
    
    # 4. 상세 정보 (상세 페이지가 다른 문자열 경로보다 아래에 있는 것이 안전합니다)
    path("<int:pk>/", views.restaurant_detail, name="detail"),
    
    # 5. [신규] 음식점 삭제 (폐업 관리)
    path("<int:pk>/delete/", views.restaurant_delete, name="delete"),
]