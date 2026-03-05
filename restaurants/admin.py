from django.contrib import admin
from .models import Restaurant, Category, Tag, RestaurantTag, MenuItem, RestaurantImage


class RestaurantTagInline(admin.TabularInline):
    model = RestaurantTag
    extra = 1


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'lat', 'lng')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'address')
    inlines = [RestaurantTagInline]
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'description', 'address', 'category')
        }),
        ('위치 정보', {
            'fields': ('lat', 'lng'),
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'emoji', 'name')
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'name', 'price', 'category', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'restaurant__name')
