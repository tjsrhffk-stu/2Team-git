from django.urls import path
from . import views

app_name = "restaurants"

urlpatterns = [
    # 목록/검색
    path("", views.restaurant_list, name="list"),

    # 지도
    path("map/", views.restaurant_map, name="map"),

    # 등록 (사장/관리자만)
    path("create/", views.restaurant_create, name="create"),

    # 상세
    path("<int:pk>/", views.restaurant_detail, name="detail"),

    # 수정 (사장/관리자만) - 기존 update URL 유지 + edit 별칭도 제공
    path("<int:pk>/update/", views.restaurant_update, name="update"),
    path("<int:pk>/edit/", views.restaurant_edit, name="edit"),

    # 삭제 (사장 본인 또는 관리자)
    path("<int:pk>/delete/", views.restaurant_delete, name="delete"),
]
