from django.contrib import admin
from .models import Review, ReviewReply, ReviewLike, ReviewReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display   = ['restaurant', 'author', 'rating', 'created_at']
    list_filter    = ['rating']
    search_fields  = ['restaurant__name', 'author__username']
    ordering       = ['-created_at']


@admin.register(ReviewLike)
class ReviewLikeAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'created_at']
    search_fields = ['review__restaurant__name', 'user__username']


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display  = ['review', 'reporter', 'reason', 'created_at']
    list_filter   = ['reason']
    search_fields = ['review__restaurant__name', 'reporter__username']
    ordering      = ['-created_at']