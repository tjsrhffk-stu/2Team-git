from django.urls import path
from . import views
from . import reservation_views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('signup-owner/', views.signup_owner_view, name='signup_owner'),
    path('logout/', views.logout_view, name='logout'),

    path('mypage/', views.mypage_view, name='mypage'),
    path('edit/', views.edit_profile, name='edit'),

    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),

    path('find-id/', views.find_id, name='find_id'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),

    # -----------------------------
    # 예약 (Reservation)
    # -----------------------------
    path('reservations/new/<int:restaurant_id>/', reservation_views.reservation_create, name='reservation_create'),
    path('reservations/my/', reservation_views.reservation_my_list, name='reservation_my_list'),
    path('reservations/<int:reservation_id>/edit/', reservation_views.reservation_edit, name='reservation_edit'),
    path('reservations/<int:reservation_id>/cancel/', reservation_views.reservation_cancel_by_customer, name='reservation_cancel'),

    # 사장: 내 식당 예약 목록 / 취소
    path('reservations/owner/', reservation_views.reservation_owner_list, name='reservation_owner_list'),
    path('reservations/<int:reservation_id>/owner-cancel/', reservation_views.reservation_cancel_by_owner, name='reservation_owner_cancel'),

    path('delete-account/', views.delete_account, name='delete_account'),
]