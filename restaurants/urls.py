from django.urls import path
from . import views

app_name = "restaurants"

urlpatterns = [
    # 목록/검색
    path("", views.restaurant_list, name="list"),

    # 자동완성 API
    path("autocomplete/", views.restaurant_autocomplete, name="autocomplete"),

    # 베스트 랭킹
    path("ranking/", views.restaurant_ranking, name="ranking"),

    # 지도
    path("map/", views.restaurant_map, name="map"),
    path("map/api/", views.restaurant_map_api, name="map_api"),

    # 등록 (사장/관리자만)
    path("create/", views.restaurant_create, name="create"),

    # 상세
    path("<int:pk>/", views.restaurant_detail, name="detail"),

    # 수정 (사장/관리자만) - 기존 update URL 유지 + edit 별칭도 제공
    path("<int:pk>/update/", views.restaurant_update, name="update"),
    path("<int:pk>/edit/", views.restaurant_edit, name="edit"),

    # 삭제 (사장 본인 또는 관리자)
    path("<int:pk>/delete/", views.restaurant_delete, name="delete"),

    # ── 메뉴 CRUD ──
    path("<int:pk>/menu/add/", views.menu_item_create, name="menu_add"),
    path("<int:pk>/menu/<int:item_pk>/update/", views.menu_item_update, name="menu_update"),
    path("<int:pk>/menu/<int:item_pk>/delete/", views.menu_item_delete, name="menu_delete"),

    # ── 태그 토글 (AJAX) ──
    path("<int:pk>/tag/<int:tag_pk>/toggle/", views.restaurant_tag_toggle, name="tag_toggle"),
]
