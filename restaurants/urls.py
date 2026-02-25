from django.urls import path
from . import views

app_name = "restaurants"

urlpatterns = [
    path("", views.restaurant_list, name="list"),
    path("<int:pk>/", views.restaurant_detail, name="detail"),
    path("create/", views.restaurant_create, name="create"),
    path('map/', views.restaurant_map, name='restaurant_map'),
    path('create/', views.restaurant_create, name='restaurant_create'),
] 


