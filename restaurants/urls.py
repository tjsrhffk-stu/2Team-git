from django.urls import path
from . import views

app_name = "restaurants"

urlpatterns = [
    path("", views.restaurant_list, name="list"),
    path("map/", views.restaurant_map, name="map"),
    path("create/", views.restaurant_create, name="create"),
    path("<int:pk>/", views.restaurant_detail, name="detail"),

    # ✅ 사장 전용 수정/삭제
    path("<int:pk>/edit/", views.restaurant_edit, name="edit"),
    path("<int:pk>/delete/", views.restaurant_delete, name="delete"),
]