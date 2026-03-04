from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("ai-search/", views.ai_search, name="ai_search"),
    path("core/notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
]
