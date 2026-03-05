from django.contrib import admin
from .models import FoodStory, Notification


@admin.register(FoodStory)
class FoodStoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'title', 'badge', 'is_published', 'order', 'created_at')
    list_editable = ('is_published', 'order')
    list_filter   = ('is_published',)
    search_fields = ('title', 'subtitle')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('recipient', 'message', 'is_read', 'created_at')
    list_filter   = ('is_read',)
    search_fields = ('recipient__username', 'message')
