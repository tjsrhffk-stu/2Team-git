import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives


# -------------------------------------------------------
# 로그인
# -------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'환영해요, {user.username}님! 🎉')
            return redirect(request.GET.get('next', '/'))
        else:
            messages.error(request, '아이디 또는 비밀번호가 올바르지 않아요.')
            return render(request, 'users/login.html', {'username': username})

    return render(request, 'users/login.html')


# -------------------------------------------------------
# 회원가입 + 이메일 인증 발송
# -------------------------------------------------------
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username or not email:
            messages.error(request, '아이디와 이메일을 입력해주세요.')
            return render(request, 'users/signup.html', {'username': username, 'email': email})

        if password1 != password2:
            messages.error(request, '비밀번호가 일치하지 않아요.')
            return render(request, 'users/signup.html', {'username': username, 'email': email})

        if len(password1) < 8:
            messages.error(request, '비밀번호는 8자 이상이어야 해요.')
            return render(request, 'users/signup.html', {'username': username, 'email': email})

        if User.objects.filter(username=username).exists():
            messages.error(request, '이미 존재하는 아이디예요.')
            return render(request, 'users/signup.html', {'username': username, 'email': email})

        if User.objects.filter(email=email).exists():
            messages.error(request, '이미 사용 중인 이메일이에요.')
            return render(request, 'users/signup.html', {'username': username, 'email': email})

        user = User.objects.create_user(username=username, email=email, password=password1)

        # 이메일 인증 토큰 생성 + 저장
        token = uuid.uuid4().hex
        user.profile.email_token = token
        user.profile.email_token_created_at = timezone.now()
        user.is_active = False
        user.save()

        # 이메일 발송
        verify_url = f"{settings.SITE_URL}/users/verify-email/{token}/"
        subject = "[LocalEats] 이메일 인증을 완료해주세요"
        html_content = f"""
        <p>안녕하세요 {username}님!</p>
        <p>아래 링크를 눌러 이메일 인증을 완료해주세요:</p>
        <a href="{verify_url}">{verify_url}</a>
        <p>(24시간 이내에 인증해야 합니다)</p>
        """

        email_message = EmailMultiAlternatives(
            subject=subject,
            body="이메일 인증을 완료해주세요.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

        return render(request, 'users/signup_done.html', {'email': email})

    return render(request, 'users/signup.html')


# -------------------------------------------------------
# 로그아웃
# -------------------------------------------------------
def logout_view(request):
    logout(request)
    messages.success(request, '로그아웃 됐어요 👋')
    return redirect('/')


# -------------------------------------------------------
# 마이페이지
# -------------------------------------------------------
@login_required
def mypage_view(request):
    return render(request, 'users/mypage.html')


# -------------------------------------------------------
# 이메일 인증 처리
# -------------------------------------------------------
def verify_email(request, token):
    user = get_object_or_404(User, profile__email_token=token)

    created_at = user.profile.email_token_created_at
    if created_at and timezone.now() > created_at + timedelta(hours=24):
        messages.error(request, '인증 링크가 만료됐어요. 다시 회원가입 해주세요.')
        return redirect('/users/signup/')

    user.is_active = True
    user.profile.email_token = None
    user.profile.email_token_created_at = None
    user.save()

    messages.success(request, '이메일 인증이 완료됐어요! 이제 로그인할 수 있어요 ✅')
    return redirect('/users/login/')


# -------------------------------------------------------
# 프로필 수정(이메일 변경/비밀번호 변경)
# -------------------------------------------------------
@login_required
def edit_profile(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        # 기본 정보 수정
        if action == 'info':
            email = request.POST.get('email', '').strip()

            if email and email != request.user.email:
                if User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                    messages.error(request, '이미 사용 중인 이메일이에요.')
                    return redirect('/users/edit/')
                request.user.email = email
                request.user.save()
                messages.success(request, '프로필이 수정됐어요! ✅')

        # 비밀번호 변경
        elif action == 'password':
            current_pw  = request.POST.get('current_password', '')
            new_pw      = request.POST.get('new_password', '')
            new_pw2     = request.POST.get('new_password2', '')

            if not request.user.check_password(current_pw):
                messages.error(request, '현재 비밀번호가 올바르지 않아요.')
                return redirect('/users/edit/')

            if len(new_pw) < 8:
                messages.error(request, '새 비밀번호는 8자 이상이어야 해요.')
                return redirect('/users/edit/')

            if new_pw != new_pw2:
                messages.error(request, '새 비밀번호가 일치하지 않아요.')
                return redirect('/users/edit/')

            request.user.set_password(new_pw)
            request.user.save()

            # ✅ 비밀번호 변경 후 즉시 로그아웃 -> 새 비밀번호로 다시 로그인
            logout(request)
            messages.success(request, '비밀번호가 변경됐어요! 새 비밀번호로 다시 로그인해주세요. 🔒')
            return redirect('/users/login/')

        return redirect('/users/edit/')

    return render(request, 'users/edit_profile.html')


# -------------------------------------------------------
# 비밀번호 찾기 (이메일 발송)
# -------------------------------------------------------
def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, '해당 이메일로 가입된 계정이 없어요.')
            return render(request, 'users/forgot_password.html', {'email': email})

        token = uuid.uuid4().hex
        user.profile.reset_token = token
        user.profile.reset_token_created_at = timezone.now()
        user.profile.save()

        reset_url = f"{settings.SITE_URL}/users/reset-password/{token}/"
        subject = "[LocalEats] 비밀번호 재설정 안내"
        html_content = f"""
        <p>안녕하세요 {user.username}님!</p>
        <p>아래 링크를 눌러 비밀번호를 재설정해주세요:</p>
        <a href="{reset_url}">{reset_url}</a>
        <p>(1시간 이내에만 유효합니다)</p>
        """

        email_message = EmailMultiAlternatives(
            subject=subject,
            body="비밀번호 재설정 링크를 확인해주세요.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

        return render(request, 'users/forgot_password_done.html', {'email': email})

    return render(request, 'users/forgot_password.html')


# -------------------------------------------------------
# 비밀번호 재설정 (토큰)
# -------------------------------------------------------
def reset_password(request, token):
    if request.user.is_authenticated:
        return redirect('/')

    user = get_object_or_404(User, profile__reset_token=token)

    created_at = user.profile.reset_token_created_at
    if created_at and timezone.now() > created_at + timedelta(hours=1):
        messages.error(request, '재설정 링크가 만료됐어요. 다시 시도해주세요.')
        return redirect('/users/forgot-password/')

    if request.method == 'POST':
        pw1 = request.POST.get('password1', '')
        pw2 = request.POST.get('password2', '')

        if pw1 != pw2:
            messages.error(request, '비밀번호가 일치하지 않아요.')
            return render(request, 'users/reset_password.html', {'token': token})

        if len(pw1) < 8:
            messages.error(request, '비밀번호는 8자 이상이어야 해요.')
            return render(request, 'users/reset_password.html', {'token': token})

        user.set_password(pw1)
        user.profile.reset_token = None
        user.profile.reset_token_created_at = None
        user.save()

        messages.success(request, '비밀번호가 재설정됐어요! 이제 로그인해주세요 ✅')
        return redirect('/users/login/')

    return render(request, 'users/reset_password.html', {'token': token})


# -------------------------------------------------------
# 회원 탈퇴 (비밀번호 확인)
# -------------------------------------------------------
@login_required
def delete_account(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')

        if not request.user.check_password(password):
            messages.error(request, '비밀번호가 올바르지 않아요.')
            return redirect('/users/delete-account/')

        request.user.delete()
        messages.success(request, '회원 탈퇴가 완료됐어요. 이용해주셔서 감사합니다 🙏')
        return redirect('/')

    return render(request, 'users/delete_account.html')