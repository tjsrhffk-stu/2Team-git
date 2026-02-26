from django.urls import path
from . import views

app_name = "favorites"

urlpatterns = [
    # 1. 즐겨찾기 목록 (views.favorite_list와 연결)
    path("", views.favorite_list, name="list"),
    
    # 2. 최근 본 맛집 목록 (views.recent_list와 연결)
    path("recent/", views.recent_list, name="recent"),
    
    # 3. 즐겨찾기 토글
    path("toggle/<int:restaurant_id>/", views.toggle_favorite, name="toggle"),
]