from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from restaurants.models import Restaurant
from .models import Profile
from .reservation_models import Reservation


def _can_book(request):
    """예약자 기능(생성/내예약/수정/취소)은 CUSTOMER + OWNER 둘 다 허용"""
    return (
        hasattr(request.user, "profile")
        and request.user.profile.user_type in (Profile.UserType.CUSTOMER, Profile.UserType.OWNER)
    )


def _require_owner(request):
    """사장 기능(내 식당 예약현황/취소)은 OWNER만 허용"""
    return hasattr(request.user, "profile") and request.user.profile.user_type == Profile.UserType.OWNER


def _parse_datetime_local(value: str):
    # input[type=datetime-local] -> aware datetime
    # 예: '2026-02-27T14:30'
    if not value:
        return None
    try:
        naive = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    return timezone.make_aware(naive, timezone.get_current_timezone())


# -----------------------------
# 예약(예약자 기능): 예약 생성
# -----------------------------
@login_required
def reservation_create(request, restaurant_id):
    if not _can_book(request):
        return HttpResponseForbidden("로그인한 사용자만 접근할 수 있어요.")

    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    if request.method == "POST":
        reserved_at = _parse_datetime_local(request.POST.get("reserved_at", "").strip())
        party_size_raw = request.POST.get("party_size", "1").strip()
        request_note = request.POST.get("request_note", "").strip()

        try:
            party_size = int(party_size_raw)
        except ValueError:
            party_size = 0

        if not reserved_at:
            messages.error(request, "예약 날짜/시간을 올바르게 입력해주세요.")
            return render(request, "users/reservations/create.html", {"restaurant": restaurant})

        if party_size <= 0:
            messages.error(request, "인원은 1명 이상으로 입력해주세요.")
            return render(request, "users/reservations/create.html", {"restaurant": restaurant})

        Reservation.objects.create(
            user=request.user,
            restaurant=restaurant,
            reserved_at=reserved_at,
            party_size=party_size,
            request_note=request_note,
            status=Reservation.Status.REQUESTED,
        )

        messages.success(request, "예약이 완료됐어요! (신청 완료)")
        return redirect("restaurants:detail", pk=restaurant.id)

    return render(request, "users/reservations/create.html", {"restaurant": restaurant})


# -----------------------------
# 예약(예약자 기능): 내 예약 목록
# ✅ 취소(CANCELED)는 목록에서 제외 (취소 시 delete라 원칙적으로 남지 않음)
# -----------------------------
@login_required
def reservation_my_list(request):
    if not _can_book(request):
        return HttpResponseForbidden("로그인한 사용자만 접근할 수 있어요.")

    reservations = (
        Reservation.objects.select_related("restaurant")
        .filter(user=request.user)
        .exclude(status=Reservation.Status.CANCELED)
        .order_by("-created_at")
    )
    return render(request, "users/reservations/my_list.html", {"reservations": reservations})


# -----------------------------
# 예약(예약자 기능): 예약 수정
# - CUSTOMER/OWNER 둘 다 가능 (단, 본인 예약만)
# ✅ 취소/거절(CANCELED/REJECTED)은 수정 불가
# -----------------------------
@login_required
def reservation_edit(request, reservation_id):
    if not _can_book(request):
        return HttpResponseForbidden("로그인한 사용자만 접근할 수 있어요.")

    reservation = get_object_or_404(
        Reservation.objects.select_related("restaurant"),
        id=reservation_id,
        user=request.user,
    )

    if reservation.status in (Reservation.Status.CANCELED, Reservation.Status.REJECTED):
        messages.error(request, "취소/거절된 예약은 수정할 수 없어요.")
        return redirect("users:reservation_my_list")

    if request.method == "POST":
        reserved_at = _parse_datetime_local(request.POST.get("reserved_at", "").strip())
        party_size_raw = request.POST.get("party_size", "1").strip()
        request_note = request.POST.get("request_note", "").strip()

        try:
            party_size = int(party_size_raw)
        except ValueError:
            party_size = 0

        if not reserved_at:
            messages.error(request, "예약 날짜/시간을 올바르게 입력해주세요.")
            return render(request, "users/reservations/edit.html", {"reservation": reservation})

        if party_size <= 0:
            messages.error(request, "인원은 1명 이상으로 입력해주세요.")
            return render(request, "users/reservations/edit.html", {"reservation": reservation})

        reservation.reserved_at = reserved_at
        reservation.party_size = party_size
        reservation.request_note = request_note
        reservation.save(update_fields=["reserved_at", "party_size", "request_note", "updated_at"])

        messages.success(request, "예약이 수정됐어요.")
        return redirect("users:reservation_my_list")

    return render(request, "users/reservations/edit.html", {"reservation": reservation})


# -----------------------------
# 예약(예약자 기능): 예약 취소 (DB에서 완전 삭제)
# -----------------------------
@login_required
@require_POST
def reservation_cancel_by_customer(request, reservation_id):
    if not _can_book(request):
        return HttpResponseForbidden("로그인한 사용자만 접근할 수 있어요.")

    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    # ✅ DB에서 완전 삭제
    reservation.delete()
    messages.success(request, "예약이 취소(삭제)됐어요.")
    return redirect("users:reservation_my_list")


# ✅ (중요) 템플릿/urls에서 보통 쓰는 이름을 맞추기 위한 별칭 함수
# - 템플릿에서 {% url 'users:reservation_cancel' res.id %} 를 쓰는 경우가 많아서 추가
@login_required
@require_POST
def reservation_cancel(request, reservation_id):
    return reservation_cancel_by_customer(request, reservation_id)


# -----------------------------
# 사장 기능: 내 식당 예약 목록
# - OWNER만 가능
# - 내 식당(restaurant.owner = request.user)에 들어온 예약만 조회
# ✅ 취소(CANCELED)는 제외 (취소 시 delete라 남지 않음)
# -----------------------------
@login_required
def reservation_owner_list(request):
    if not _require_owner(request):
        return HttpResponseForbidden("사장만 접근할 수 있어요.")

    reservations = (
        Reservation.objects.select_related("restaurant", "user")
        .filter(restaurant__owner=request.user)
        .exclude(status=Reservation.Status.CANCELED)
        .order_by("-created_at")
    )
    return render(request, "users/reservations/owner_list.html", {"reservations": reservations})


# -----------------------------
# 사장 기능: 예약 취소 (DB에서 완전 삭제)
# -----------------------------
@login_required
@require_POST
def reservation_cancel_by_owner(request, reservation_id):
    if not _require_owner(request):
        return HttpResponseForbidden("사장만 접근할 수 있어요.")

    reservation = get_object_or_404(
        Reservation.objects.select_related("restaurant"),
        id=reservation_id,
        restaurant__owner=request.user,
    )

    # ✅ DB에서 완전 삭제
    reservation.delete()
    messages.success(request, "예약을 취소(삭제) 처리했어요.")
    return redirect("users:reservation_owner_list")


# ✅ (중요) 템플릿/urls에서 보통 쓰는 이름을 맞추기 위한 별칭 함수
# - 템플릿에서 {% url 'users:reservation_owner_cancel' r.id %} 를 쓰는 경우가 많아서 추가
@login_required
@require_POST
def reservation_owner_cancel(request, reservation_id):
    return reservation_cancel_by_owner(request, reservation_id)


# -----------------------------
# 사장 기능: 예약 확정 (REQUESTED → CONFIRMED)
# -----------------------------
@login_required
@require_POST
def reservation_confirm(request, reservation_id):
    if not _require_owner(request):
        return HttpResponseForbidden("사장만 접근할 수 있어요.")

    reservation = get_object_or_404(
        Reservation.objects.select_related("restaurant"),
        id=reservation_id,
        restaurant__owner=request.user,
    )

    if reservation.status != Reservation.Status.REQUESTED:
        messages.error(request, "신청 상태의 예약만 확정할 수 있어요.")
        return redirect("users:reservation_owner_list")

    reservation.status = Reservation.Status.CONFIRMED
    reservation.save(update_fields=["status"])
    messages.success(request, "예약을 확정했어요! ✅")
    return redirect("users:reservation_owner_list")


# -----------------------------
# 사장 기능: 예약 거절 (REQUESTED/CONFIRMED → REJECTED)
# -----------------------------
@login_required
@require_POST
def reservation_reject(request, reservation_id):
    if not _require_owner(request):
        return HttpResponseForbidden("사장만 접근할 수 있어요.")

    reservation = get_object_or_404(
        Reservation.objects.select_related("restaurant"),
        id=reservation_id,
        restaurant__owner=request.user,
    )

    if reservation.status == Reservation.Status.CANCELED:
        messages.error(request, "이미 취소된 예약이에요.")
        return redirect("users:reservation_owner_list")

    reservation.status = Reservation.Status.REJECTED
    reservation.save(update_fields=["status"])
    messages.success(request, "예약을 거절했어요.")
    return redirect("users:reservation_owner_list")