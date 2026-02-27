from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Restaurant, Category, RestaurantImage

import os, environ
from django.conf import settings

# ✅ 추가된 부분: env 객체 초기화 (NameError 해결)
env = environ.Env()
environ.Env.read_env()

def _extract_form_data(post):
    """기존 팀원이 만든 폼 데이터 추출 함수 유지"""
    # ✅ break_time 키가 포함되어 있는지 확인
    keys = ["name", "category", "phone", "description", "address", "hours", "break_time", "closed_days", "website"]
    if hasattr(post, "get"):
        return {k: (post.get(k, "") or "") for k in keys}
    return {k: "" for k in keys}


def _is_owner_user(user) -> bool:
    """기존 권한 판별 로직 유지"""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if hasattr(user, "owner_profile") or getattr(user, "is_staff", False):
        return True
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "user_type", None) == "OWNER":
        return True
    return False


def restaurant_list(request):
    """음식점 목록 뷰"""
    q = request.GET.get("q", "")
    restaurants = Restaurant.objects.all().order_by("-id")
    if q:
        restaurants = restaurants.filter(
            Q(name__icontains=q) | Q(category__name__icontains=q) | Q(address__icontains=q)
        )
    return render(request, "restaurants/list.html", {"restaurants": restaurants, "q": q})


def restaurant_map(request):
    """지도 탐색 뷰"""
    q = request.GET.get("q", "")
    restaurants = Restaurant.objects.exclude(lat__isnull=True).exclude(lng__isnull=True)
    if q:
        restaurants = restaurants.filter(
            Q(name__icontains=q) | Q(category__name__icontains=q) | Q(address__icontains=q)
        )
    return render(request, "Maps_API.html", {"restaurants": restaurants, "q": q})


def restaurant_detail(request, pk):
    """상세 페이지 뷰 - 환경 변수 키 전달 추가"""
    restaurant = get_object_or_404(Restaurant, pk=pk)
    reviews = restaurant.reviews.all().order_by("-created_at")
    total_reviews = reviews.count()
    
    rating_distribution = []
    for i in range(5, 0, -1):
        count = reviews.filter(rating=i).count()
        pct = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_distribution.append({"star": i, "count": count, "pct": int(pct)})
    
    context = {
        "restaurant": restaurant,
        "reviews": reviews,
        "rating_distribution": rating_distribution,
        "MAP_API_KEY": settings.NAVER_CLIENT_ID, 
    }
    
    return render(request, "restaurants/detail.html", context)


@login_required
def restaurant_create(request):
    """음식점 등록 뷰"""
    if not _is_owner_user(request.user):
        messages.error(request, "사장님 계정만 등록이 가능합니다.")
        return redirect("restaurants:list")

    template_name = "restaurants/form.html"
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_pk = request.POST.get("category")
        address = request.POST.get("address", "").strip()

        if not (name and address):
            messages.error(request, "필수 항목을 입력해주세요.")
            return render(request, template_name, {
                "mode": "create",
                "categories": Category.objects.all(),
                "form_data": _extract_form_data(request.POST)
            })

        restaurant = Restaurant.objects.create(
            owner=request.user,
            name=name,
            address=address,
            category_id=category_pk if category_pk else None,
            phone=request.POST.get("phone", "").strip(),
            description=request.POST.get("description", "").strip(),
            hours=request.POST.get("hours", "").strip(),
            # ✅ 추가: 브레이크 타임 저장
            break_time=request.POST.get("break_time", "").strip(),
            closed_days=request.POST.get("closed_days", "").strip(),
            website=request.POST.get("website", "").strip(),
            thumbnail=request.FILES.get("thumbnail")
        )

        additional_images = request.FILES.getlist("additional_images")
        for idx, img in enumerate(additional_images):
            if idx < 10:
                RestaurantImage.objects.create(restaurant=restaurant, image=img)

        messages.success(request, f"'{restaurant.name}' 등록 완료.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    categories = Category.objects.all()
    return render(request, template_name, {"mode": "create", "categories": categories, "form_data": _extract_form_data({})})


@login_required
def restaurant_update(request, pk):
    """음식점 수정 뷰"""
    restaurant = get_object_or_404(Restaurant, pk=pk)
    old_address = restaurant.address

    if not (_is_owner_user(request.user) and restaurant.owner == request.user) and \
       not request.user.is_staff:
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("restaurants:detail", pk=pk)

    template_name = "restaurants/form.html"

    if request.method == "POST":
        restaurant.name = request.POST.get("name", "").strip()
        restaurant.phone = request.POST.get("phone", "").strip()
        new_address = request.POST.get("address", "").strip()
        restaurant.description = request.POST.get("description", "").strip()
        restaurant.hours = request.POST.get("hours", "").strip()
        
        # ✅ 추가: 브레이크 타임 수정 반영
        restaurant.break_time = request.POST.get("break_time", "").strip()
        
        restaurant.closed_days = request.POST.get("closed_days", "").strip()
        restaurant.website = request.POST.get("website", "").strip()

        category_pk = request.POST.get("category")
        if category_pk:
            restaurant.category_id = category_pk

        if request.FILES.get("thumbnail"):
            restaurant.thumbnail = request.FILES.get("thumbnail")

        if old_address != new_address:
            restaurant.address = new_address
            restaurant.lat, restaurant.lng = None, None

        restaurant.save()

        additional_images = request.FILES.getlist("additional_images")
        if additional_images:
            current_count = restaurant.additional_images.count()
            for img in additional_images:
                if current_count < 10:
                    RestaurantImage.objects.create(restaurant=restaurant, image=img)
                    current_count += 1

        messages.success(request, "성공적으로 수정되었습니다.")
        return redirect("restaurants:detail", pk=pk)

    categories = Category.objects.all()
    return render(request, template_name, {
        "mode": "update", 
        "restaurant": restaurant, 
        "categories": categories,
        "form_data": restaurant
    })


@login_required
def restaurant_delete(request, pk):
    """음식점 삭제 뷰"""
    restaurant = get_object_or_404(Restaurant, pk=pk)
    if not (restaurant.owner == request.user or request.user.is_staff):
        messages.error(request, "삭제 권한이 없습니다.")
        return redirect("restaurants:detail", pk=pk)

    if request.method == "POST":
        restaurant.delete()
        messages.success(request, "삭제되었습니다.")
        return redirect("restaurants:list")
    return render(request, "restaurants/confirm_delete.html", {"restaurant": restaurant})


def restaurant_edit(request, pk):
    """기존 URL 호환용"""
    return redirect("restaurants:update", pk=pk)