from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display   = ['restaurant', 'author', 'rating', 'created_at']
    list_filter    = ['rating']
    search_fields  = ['restaurant__name', 'author__username']
    ordering       = ['-created_at']