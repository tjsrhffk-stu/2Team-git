from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import CustomerUser, OwnerUser, CustomerProfile, OwnerProfile


# ✅ 기본 auth.User 제거 (AUTHENTICATION 섹션 Users 없애기)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


# ----------------------------
# Inline: User 편집 화면에서 같이 보기
# ----------------------------
class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False
    extra = 0


class OwnerProfileInline(admin.StackedInline):
    model = OwnerProfile
    can_delete = False
    extra = 0


# ----------------------------
# 1) 전체 유저(Users) 강제 등록
# ----------------------------
class AllUsersAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    inlines = [CustomerProfileInline, OwnerProfileInline]


# ✅ 혹시 중복 등록되어있을 수도 있으니 한번 더 안전하게 unregister
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, AllUsersAdmin)


# ----------------------------
# 2) 일반 유저(Customer Users)
# ----------------------------
@admin.register(CustomerUser)
class CustomerUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    inlines = [CustomerProfileInline, OwnerProfileInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("profile")
        return qs.filter(profile__user_type="CUSTOMER")


# ----------------------------
# 3) 사장 유저(Owner Users)
# ----------------------------
@admin.register(OwnerUser)
class OwnerUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    inlines = [CustomerProfileInline, OwnerProfileInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("profile")
        return qs.filter(profile__user_type="OWNER")


# ✅ Customers/Owners 메뉴 숨기기
try:
    admin.site.unregister(CustomerProfile)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(OwnerProfile)
except admin.sites.NotRegistered:
    pass