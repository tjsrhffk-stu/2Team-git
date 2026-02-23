from django.urls import path
from . import views

app_name = "favorites"

urlpatterns = [
    path("toggle/<int:restaurant_id>/", views.toggle_favorite, name="toggle"),
    path("", views.favorite_list, name="list"),
]