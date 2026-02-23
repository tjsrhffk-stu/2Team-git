import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
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
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # 유효성 검사
        if not username or len(username) < 4:
            return render(request, 'users/signup.html', {'errors': {'username': '아이디는 4자 이상이어야 해요.'}, 'username': username, 'email': email})
        if User.objects.filter(username=username).exists():
            return render(request, 'users/signup.html', {'errors': {'username': '이미 사용 중인 아이디예요.'}, 'username': username, 'email': email})
        if not email:
            return render(request, 'users/signup.html', {'errors': {'email': '이메일을 입력해주세요.'}, 'username': username, 'email': email})
        if len(password1) < 8 or password1 != password2:
            return render(request, 'users/signup.html', {'errors': {'password1': '비밀번호를 확인해주세요.'}, 'username': username, 'email': email})

        # 유저 생성
        user = User.objects.create_user(username=username, email=email, password=password1, is_active=False)

        token = str(uuid.uuid4())
        try:
            from .models import EmailVerificationToken
            EmailVerificationToken.objects.create(user=user, token=token)
            verify_url = f"{settings.SITE_URL}/users/verify-email/{token}/"
            subject = '[LocalEats] 이메일 인증'
            text_content = verify_url
            html_content = f'<a href="{verify_url}">이메일 인증하기 클릭</a>'

            msg = EmailMultiAlternatives(
              subject=subject,
              body=text_content,
              from_email=settings.DEFAULT_FROM_EMAIL,
              to=[email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
        except Exception as e:
            print(f"오류: {e}")

        return render(request, 'users/signup_done.html', {'email': email})

    return render(request, 'users/signup.html', {'errors': {}, 'username': '', 'email': ''})


# -------------------------------------------------------
# 이메일 인증 확인
# -------------------------------------------------------
def verify_email(request, token):
    from .models import EmailVerificationToken
    try:
        token_obj = EmailVerificationToken.objects.get(token=token)
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, '유효하지 않은 인증 링크예요.')
        return redirect('/users/login/')

    # 24시간 만료 체크
    if timezone.now() > token_obj.created_at + timedelta(hours=24):
        token_obj.delete()
        messages.error(request, '인증 링크가 만료됐어요. 다시 회원가입해주세요.')
        return redirect('/users/signup/')

    # 유저 활성화
    user = token_obj.user
    user.is_active = True
    user.save()
    token_obj.delete()

    login(request, user)
    messages.success(request, '이메일 인증이 완료됐어요! 🎉')
    return redirect('/')


# -------------------------------------------------------
# 로그아웃
# -------------------------------------------------------
def logout_view(request):
    logout(request)
    messages.success(request, '로그아웃 됐어요. 다음에 또 만나요! 👋')
    return redirect('/')


# -------------------------------------------------------
# 마이페이지
# -------------------------------------------------------
@login_required
def mypage_view(request):
    from reviews.models import Review
    reviews = Review.objects.filter(
        author=request.user
    ).select_related('restaurant').order_by('-created_at')

    favorites = []
    favorite_count = 0
    try:
        from favorites.models import Favorite
        favorites = Favorite.objects.filter(
            user=request.user
        ).select_related('restaurant').order_by('-created_at')
        favorite_count = favorites.count()
    except Exception:
        pass

    return render(request, 'users/mypage.html', {
        'reviews': reviews,
        'favorites': favorites,
        'favorite_count': favorite_count,
    })


# -------------------------------------------------------
# 프로필 수정 (닉네임/이메일/비밀번호 변경)
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
            update_session_auth_hash(request, request.user)  # 로그인 유지
            messages.success(request, '비밀번호가 변경됐어요! 🔒')

        return redirect('/users/edit/')

    return render(request, 'users/edit_profile.html')


# -------------------------------------------------------
# 비밀번호 찾기 (이메일 발송)
# -------------------------------------------------------
def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 보안상 존재 여부를 알려주지 않음
            return render(request, 'users/forgot_password_done.html', {'email': email})

        # 재설정 토큰 생성
        token = str(uuid.uuid4())
        from .models import PasswordResetToken
        PasswordResetToken.objects.filter(user=user).delete()  # 기존 토큰 삭제
        PasswordResetToken.objects.create(user=user, token=token)

        # 재설정 이메일 발송
        reset_url = f"{settings.SITE_URL}/users/reset-password/{token}/"
        send_mail(
            subject='[LocalEats] 비밀번호 재설정',
            message=f'''
안녕하세요!

비밀번호 재설정 요청이 들어왔어요.

아래 링크를 클릭해서 비밀번호를 재설정해주세요:
{reset_url}

이 링크는 1시간 후에 만료돼요.
본인이 요청하지 않았다면 이 이메일을 무시해주세요.

감사합니다,
LocalEats 팀
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return render(request, 'users/forgot_password_done.html', {'email': email})

    return render(request, 'users/forgot_password.html')


# -------------------------------------------------------
# 비밀번호 재설정
# -------------------------------------------------------
def reset_password(request, token):
    from .models import PasswordResetToken
    try:
        token_obj = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, '유효하지 않은 링크예요.')
        return redirect('/users/forgot-password/')

    # 1시간 만료 체크
    if timezone.now() > token_obj.created_at + timedelta(hours=1):
        token_obj.delete()
        messages.error(request, '링크가 만료됐어요. 다시 요청해주세요.')
        return redirect('/users/forgot-password/')

    if request.method == 'POST':
        new_pw  = request.POST.get('new_password', '')
        new_pw2 = request.POST.get('new_password2', '')

        if len(new_pw) < 8:
            messages.error(request, '비밀번호는 8자 이상이어야 해요.')
            return render(request, 'users/reset_password.html', {'token': token})

        if new_pw != new_pw2:
            messages.error(request, '비밀번호가 일치하지 않아요.')
            return render(request, 'users/reset_password.html', {'token': token})

        user = token_obj.user
        user.set_password(new_pw)
        user.save()
        token_obj.delete()

        messages.success(request, '비밀번호가 재설정됐어요! 로그인해주세요. 🔒')
        return redirect('/users/login/')

    return render(request, 'users/reset_password.html', {'token': token})


# -------------------------------------------------------
# 회원 탈퇴
# -------------------------------------------------------
@login_required
def delete_account(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')

        if not request.user.check_password(password):
            messages.error(request, '비밀번호가 올바르지 않아요.')
            return redirect('/users/delete-account/')

        user = request.user
        logout(request)
        user.delete()
        messages.success(request, '계정이 삭제됐어요. 그동안 이용해주셔서 감사해요 💙')
        return redirect('/')

    return render(request, 'users/delete_account.html')