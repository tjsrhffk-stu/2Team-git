from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("", views.review_list, name="list"),
    path("create/<int:restaurant_id>/", views.create_review, name="create"),
    path("<int:review_id>/edit/", views.edit_review, name="edit"),    
    path("<int:review_id>/delete/", views.delete_review, name="delete"),  
]