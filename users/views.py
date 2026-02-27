import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, Subquery  # ✅ 추가
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import OwnerProfile, Profile, CustomerProfile
from favorites.models import Favorite
from reviews.models import Review

# ✅ 이메일 인증(verification, 베리피케이션) 아직 OFF면 False
#   - 나중에 True로 바꾸면 signup_done.html + 인증 링크 발송 흐름으로 다시 쓸 수 있음
ENABLE_EMAIL_VERIFY = False


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


def _render_signup(request, pane: str = 'normal', **ctx):
    """
    signup.html(일반/사업자 탭) 다시 렌더링 헬퍼
    """
    ctx.setdefault('open_pane', pane)
    ctx.setdefault('auto_open', 1)
    return render(request, 'users/signup.html', ctx)


# -------------------------------------------------------
# ✅ 일반 회원가입
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
        if not username or not email:
            messages.error(request, '아이디와 이메일을 입력해주세요.')
            return _render_signup(request, 'normal', username=username, email=email)

        if password1 != password2:
            messages.error(request, '비밀번호가 일치하지 않아요.')
            return _render_signup(request, 'normal', username=username, email=email)

        if len(password1) < 8:
            messages.error(request, '비밀번호는 8자 이상이어야 해요.')
            return _render_signup(request, 'normal', username=username, email=email)

        if User.objects.filter(username=username).exists():
            messages.error(request, '이미 존재하는 아이디예요.')
            return _render_signup(request, 'normal', username=username, email=email)

        if User.objects.filter(email=email).exists():
            messages.error(request, '이미 사용 중인 이메일이에요.')
            return _render_signup(request, 'normal', username=username, email=email)

        # ✅ 계정 생성 (유저 + 프로필/타입까지 한 번에)
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.is_active = True
            user.save()

            # Profile 보장 + ✅ 타입을 CUSTOMER로 명시
            profile, _ = Profile.objects.get_or_create(user=user)
            # (models.py에서 user_type 필드 추가한 기준)
            if hasattr(profile, "user_type"):
                profile.user_type = "CUSTOMER"
                profile.save(update_fields=["user_type"])

            # ✅ 일반회원 프로필 보장
            CustomerProfile.objects.get_or_create(user=user)

        # 이메일 인증 ON일 때만 토큰/메일 발송
        if ENABLE_EMAIL_VERIFY:
            token = uuid.uuid4().hex
            profile.email_token = token
            profile.email_token_created_at = timezone.now()
            profile.save()

            # 인증 전에는 비활성화
            user.is_active = False
            user.save()

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

        # 이메일 인증 OFF: 바로 가입 완료
        messages.success(request, '회원가입이 완료됐어요! 이제 로그인해주세요 ✅')
        return redirect('/users/login/')

    # GET
    return render(request, 'users/signup.html', {'open_pane': 'normal', 'auto_open': 0})


# -------------------------------------------------------
# ✅ 사장(사업자) 회원가입 (사업자등록번호 포함)
#   - restaurants 쪽 권한 체크가 is_staff 기반이면, 여기서 is_staff=True로 맞춤
# -------------------------------------------------------
def signup_owner_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        business_number_raw = request.POST.get('business_number', '').strip()
        business_number = re.sub(r'[^0-9]', '', business_number_raw)  # 하이픈/공백 제거

        # 유효성 검사
        if not username or not email:
            messages.error(request, '아이디와 이메일을 입력해주세요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        if not business_number:
            messages.error(request, '사업자등록번호를 입력해주세요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        # 보통 10자리(국내 사업자등록번호) 기준
        if len(business_number) != 10:
            messages.error(request, '사업자등록번호는 숫자 10자리로 입력해주세요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        if password1 != password2:
            messages.error(request, '비밀번호가 일치하지 않아요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        if len(password1) < 8:
            messages.error(request, '비밀번호는 8자 이상이어야 해요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        if User.objects.filter(username=username).exists():
            messages.error(request, '이미 존재하는 아이디예요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        if User.objects.filter(email=email).exists():
            messages.error(request, '이미 사용 중인 이메일이에요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        if OwnerProfile.objects.filter(business_number=business_number).exists():
            messages.error(request, '이미 등록된 사업자등록번호예요.')
            return _render_signup(
                request, 'owner',
                o_username=username, o_email=email, o_business_number=business_number_raw
            )

        # ✅ 계정 생성 (유저 + 타입 + OwnerProfile까지 한 번에)
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password1)
            # user.is_staff = True          # ✅ 기존 흐름 유지(프로젝트 권한체크가 is_staff 기반이면 필요)
            user.is_active = True
            user.save()

            # Profile 보장 + ✅ 타입을 OWNER로 명시
            profile, _ = Profile.objects.get_or_create(user=user)
            if hasattr(profile, "user_type"):
                profile.user_type = "OWNER"
                profile.save(update_fields=["user_type"])

            # ✅ 사장 프로필 생성(사업자등록번호 저장)
            OwnerProfile.objects.create(user=user, business_number=business_number)

            # ✅ 일반회원 프로필이 자동 생성/존재하면 제거(데이터 꼬임 방지)
            CustomerProfile.objects.filter(user=user).delete()

        # 이메일 인증 ON일 때만 토큰/메일 발송
        if ENABLE_EMAIL_VERIFY:
            token = uuid.uuid4().hex
            profile.email_token = token
            profile.email_token_created_at = timezone.now()
            profile.save()

            user.is_active = False
            user.save()

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

        # 이메일 인증 OFF: 바로 가입 완료
        messages.success(request, '사업자 회원가입이 완료됐어요! 이제 로그인해주세요 ✅')
        return redirect('/users/login/')

    # GET: 사업자 탭 열어둔 상태로 보여주기
    return render(request, 'users/signup.html', {'open_pane': 'owner', 'auto_open': 1})


# -------------------------------------------------------
# 로그아웃
# -------------------------------------------------------
def logout_view(request):
    logout(request)
    messages.success(request, '로그아웃 됐어요 👋')
    return redirect('/')


# -------------------------------------------------------
# 마이페이지  ✅ A안(?tab=) 방식
#   ✅ 수정사항(필요한 것만):
#   1) 사장 전용 탭 추가: tab=owner_reservations 허용
#   2) 사장 탭에서 "내 식당 예약 전체" 내려주기(owner_reservations_all)
#   3) 지저분한 취소 내역 숨김: CANCELED는 exclude
# -------------------------------------------------------
@login_required
def mypage_view(request):
    tab = request.GET.get("tab", "mypage").strip().lower()

    # ✅ (수정1) 사장 탭 추가
    allowed_tabs = {"mypage", "reservations", "owner_reservations", "history", "visited", "favorites", "reviews"}
    if tab not in allowed_tabs:
        tab = "mypage"

    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related("restaurant")
        .order_by("-created_at")
    )
    favorite_count = favorites.count()

    reviews = (
        Review.objects
        .filter(author=request.user)
        .select_related("restaurant")
        .order_by("-created_at")
    )

    # ✅ 사장(OWNER)이면 내 식당 목록 내려줌
    from restaurants.models import Restaurant
    my_restaurants = Restaurant.objects.none()

    try:
        is_owner = hasattr(request.user, "profile") and request.user.profile.user_type == "OWNER"
    except Exception:
        is_owner = False

    if is_owner:
        my_restaurants = Restaurant.objects.filter(owner=request.user).order_by("-id")

    # ✅ 방문한 맛집(= 내 리뷰 중 4점 이상만)
    history_min_rating = 4

    latest_review_qs = (
        Review.objects
        .filter(
            author=request.user,
            rating__gte=history_min_rating,
            restaurant=OuterRef("pk"),
        )
        .order_by("-created_at")
    )

    visited_qs = (
        Restaurant.objects
        .annotate(
            visited_at=Subquery(latest_review_qs.values("created_at")[:1]),
            my_rating=Subquery(latest_review_qs.values("rating")[:1]),
        )
        .filter(visited_at__isnull=False)
        .order_by("-my_rating", "-visited_at")
    )

    history = [
        {"restaurant": r, "visited_at": r.visited_at, "my_rating": r.my_rating}
        for r in visited_qs
    ]

    # =====================================================
    # ✅ 예약 데이터
    # - owner_reservations: 사장 마이페이지(tab=mypage)에서 최신 5개 미리보기
    # - owner_reservations_all: (수정2) 사장 탭(tab=owner_reservations)에서 전체 목록
    # - reservations: 일반회원 마이페이지(tab=reservations)에서 본인 예약 목록
    # - (수정3) CANCELED 제외(취소는 예약뷰에서 delete로 처리할 예정이라도 안전하게 숨김)
    # =====================================================
    owner_reservations = []
    owner_reservations_all = []  # ✅ 추가(전체 목록)
    reservations = []

    try:
        from .reservation_models import Reservation
    except Exception:
        Reservation = None

    if Reservation is not None:
        # 사장: 내 식당 예약 최신 5개 (취소 제외)
        if is_owner:
            owner_reservations = (
                Reservation.objects
                .select_related("restaurant", "user")
                .filter(restaurant__owner=request.user)
                .exclude(status=Reservation.Status.CANCELED)
                .order_by("-created_at")[:5]
            )

        # ✅ (수정2) 사장: 내 식당 예약 전체 목록 (취소 제외)
        if is_owner and (tab == "owner_reservations"):
            owner_reservations_all = (
                Reservation.objects
                .select_related("restaurant", "user")
                .filter(restaurant__owner=request.user)
                .exclude(status=Reservation.Status.CANCELED)
                .order_by("-created_at")
            )

        # 일반회원(사장 아닌 경우): 내 예약 전체 (취소 제외)
        if (not is_owner) and (tab == "reservations"):
            reservations = (
                Reservation.objects
                .select_related("restaurant")
                .filter(user=request.user)
                .exclude(status=Reservation.Status.CANCELED)
                .order_by("-created_at")
            )

    context = {
        "active_tab": tab,
        "favorites": favorites,
        "favorite_count": favorite_count,
        "reviews": reviews,

        "my_restaurants": my_restaurants,
        "is_owner": is_owner,

        "history": history,
        "history_min_rating": history_min_rating,

        "owner_reservations": owner_reservations,
        "owner_reservations_all": owner_reservations_all,  # ✅ 추가
        "reservations": reservations,
    }
    return render(request, "users/mypage.html", context)


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
# 아이디 찾기 (이메일로)
# -------------------------------------------------------
def find_id(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, '이메일을 입력해주세요.')
            return render(request, 'users/find_id.html', {'email': email})

        users = User.objects.filter(email__iexact=email).order_by('date_joined')
        if not users.exists():
            messages.error(request, '해당 이메일로 가입된 계정이 없어요.')
            return render(request, 'users/find_id.html', {'email': email})

        usernames = [u.username for u in users]
        return render(request, 'users/find_id_done.html', {'email': email, 'usernames': usernames})

    return render(request, 'users/find_id.html')


# -------------------------------------------------------
# 비밀번호 찾기 (아이디 + 이메일로 확인 후 이메일 발송)
# -------------------------------------------------------
def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()

        if not username or not email:
            messages.error(request, '아이디와 이메일을 모두 입력해주세요.')
            return render(request, 'users/forgot_password.html', {'username': username, 'email': email})

        try:
            # ✅ 아이디 + 이메일이 모두 일치해야만 발송
            user = User.objects.get(username=username, email=email)
        except User.DoesNotExist:
            messages.error(request, '아이디 또는 이메일이 올바르지 않아요.')
            return render(request, 'users/forgot_password.html', {'username': username, 'email': email})

        token = uuid.uuid4().hex
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.reset_token = token
        profile.reset_token_created_at = timezone.now()
        profile.save()

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