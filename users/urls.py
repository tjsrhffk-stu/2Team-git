from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('signup-owner/', views.signup_owner_view, name='signup_owner'),  # ✅ 사업자 회원가입
    path('logout/', views.logout_view, name='logout'),

    path('mypage/', views.mypage_view, name='mypage'),
    path('edit/', views.edit_profile, name='edit'),

    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),

    # ✅ 아이디 찾기 / 비밀번호 찾기
    path('find-id/', views.find_id, name='find_id'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),

    path('delete-account/', views.delete_account, name='delete_account'),
]