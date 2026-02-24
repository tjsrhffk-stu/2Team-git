"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from restaurants import views as restaurant_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    # 이 줄을 추가하면 127.0.0.1:8000/map/ 으로 바로 접속 가능합니다.
    path("map/", restaurant_views.restaurant_map, name='restaurant_map'),
    path("restaurants/", include("restaurants.urls")),
    path("reviews/", include("reviews.urls")),
    path("favorites/", include("favorites.urls")),
    path("users/", include("users.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
