from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Restaurant, Category, RestaurantImage


def _extract_form_data(post):
    """restaurants/form.html 템플릿에서 form_data.<field>를 안전하게 사용하기 위해
    항상 필요한 키를 가진 dict로 정규화합니다."""
    keys = ["name", "category", "phone", "description", "address", "hours", "closed_days", "website"]
    if hasattr(post, "get"):
        return {k: (post.get(k, "") or "") for k in keys}
    return {k: "" for k in keys}



def _is_owner_user(user) -> bool:
    """사업자(사장) 계정 여부 판별
    - 구버전: owner_profile 존재 / is_staff
    - 신버전: users.Profile.user_type == 'OWNER'
    """
    if not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    # OwnerProfile이 있거나 staff면 사장으로 취급 (기존 로직 호환)
    if hasattr(user, "owner_profile") or getattr(user, "is_staff", False):
        return True

    # Profile.user_type 기준 (새 로직)
    try:
        return hasattr(user, "profile") and getattr(user.profile, "user_type", "") == "OWNER"
    except Exception:
        return False


# 1. 음식점 목록
def restaurant_list(request):
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "latest")

    qs = Restaurant.objects.all().annotate(
        avg_rating=Avg("reviews__rating"),
        review_count=Count("reviews")
    )

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q))

    if category_id:
        if category_id.isdigit():
            qs = qs.filter(category_id=category_id)
        else:
            qs = qs.filter(category__name=category_id)

    # 정렬 로직
    if sort == "rating":
        qs = qs.order_by("-avg_rating", "-review_count", "-id")
    elif sort == "reviews":
        qs = qs.order_by("-review_count", "-id")
    elif sort == "views":
        qs = qs.order_by("-view_count", "-id")
    else:
        qs = qs.order_by("-id")

    # 즐겨찾기 최적화
    user_favorites = []
    if request.user.is_authenticated:
        try:
            from favorites.models import Favorite
            user_favorites = Favorite.objects.filter(user=request.user).values_list("restaurant_id", flat=True)
        except (ImportError, Exception):
            pass

    context = {
        "restaurants": qs,
        "q": q,
        "categories": Category.objects.all(),
        "category_id": category_id,
        "sort": sort,
        "user_favorites": user_favorites,
    }
    return render(request, "restaurants/list.html", context)


# 2. 음식점 상세
def restaurant_detail(request, pk):
    restaurant = get_object_or_404(
        Restaurant.objects.annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews")
        ),
        pk=pk
    )

    # 조회수 증가
    Restaurant.objects.filter(pk=pk).update(view_count=restaurant.view_count + 1)

    # 리뷰 정렬
    sort = request.GET.get("sort", "rating_high")
    reviews_qs = restaurant.reviews.select_related("author")

    if sort == "latest":
        reviews = reviews_qs.order_by("-created_at")
    elif sort == "rating_low":
        reviews = reviews_qs.order_by("rating", "-created_at")
    else:
        reviews = reviews_qs.order_by("-rating", "-created_at")

    # 별점 분포
    rating_distribution = []
    total = reviews_qs.count()
    for star in range(5, 0, -1):
        count = reviews_qs.filter(rating=star).count()
        pct = (count / total * 100) if total > 0 else 0
        rating_distribution.append({'star': star, 'count': count, 'pct': round(pct)})
# 즐겨찾기 여부
    is_favorite = False
    if request.user.is_authenticated:
        try:
            from favorites.models import Favorite
            is_favorite = Favorite.objects.filter(user=request.user, restaurant=restaurant).exists()
        except (ImportError, Exception):
            pass

    context = {
        "restaurant": restaurant,
        "reviews": reviews,
        "avg_rating": round(restaurant.avg_rating, 1) if restaurant.avg_rating else 0,
        "rating_distribution": rating_distribution,
        "is_favorite": is_favorite,
        "current_sort": sort,
        # 사장(owner) 또는 관리자(staff/superuser)
        "can_manage": (
            request.user.is_authenticated
            and (request.user == restaurant.owner or request.user.is_staff or request.user.is_superuser)
        ),
    }
    return render(request, "restaurants/detail.html", context)


# 3. 음식점 등록
@login_required
def restaurant_create(request):
    if not _is_owner_user(request.user):
        messages.error(request, "사장님 계정만 식당 등록이 가능합니다.")
        return redirect("/restaurants/")

    if not Category.objects.exists():
        default_categories = ["한식", "중식", "일식", "양식", "카페", "패스트푸드", "기타"]
        for cat_name in default_categories:
            Category.objects.get_or_create(name=cat_name)

    categories = Category.objects.all()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_pk = request.POST.get("category", "").strip()
        address = request.POST.get("address", "").strip()

        if not name or not address:
            messages.error(request, "필수 항목을 입력해주세요.")
            return render(request, "restaurants/form.html", {"mode": "create", "restaurant": None, "categories": categories, "form_data": _extract_form_data(request.POST), "current_registered": 0})

        restaurant = Restaurant(
            owner=request.user,
            name=name,
            address=address,
            phone=request.POST.get("phone", "").strip(),
            description=request.POST.get("description", "").strip(),
            hours=request.POST.get("hours", "").strip(),
            closed_days=request.POST.get("closed_days", "").strip(),
            website=request.POST.get("website", "").strip(),
            thumbnail=request.FILES.get("thumbnail"),
        )

        if category_pk:
            restaurant.category = Category.objects.filter(pk=category_pk).first()

        restaurant.save()

        # 상세 사진 다중 등록 (최대 10장)
        additional_images = request.FILES.getlist("additional_images")
        for img in additional_images[:10]:
            RestaurantImage.objects.create(restaurant=restaurant, image=img)

        messages.success(request, f'"{name}" 등록 성공! 🎉')
        return redirect("restaurants:detail", pk=restaurant.pk)

    return render(request, "restaurants/form.html", {"mode": "create", "restaurant": None, "categories": categories, "form_data": _extract_form_data(request.POST), "current_registered": 0})


# 4. 지도 페이지
def restaurant_map(request):
    return render(request, "Maps_Api.html", {"restaurants": Restaurant.objects.all()})


# 5. 음식점 삭제 (사장 본인 또는 관리자)
@login_required
def restaurant_delete(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk)

    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "관리자만 삭제할 수 있습니다.")
        return redirect("restaurants:detail", pk=pk)

    if request.method == "POST":
        name = restaurant.name
        restaurant.delete()
        messages.success(request, f'"{name}" 식당 정보가 삭제되었습니다.')
        return redirect("restaurants:list")

    # ✅ 템플릿 이름 통일 (기존 main에는 템플릿이 없어서 confirm_delete.html 사용)
    return render(request, "restaurants/confirm_delete.html", {"restaurant": restaurant})


# 6. 음식점 수정 (update URL)
@login_required
def restaurant_update(request, pk):
    return _restaurant_update_impl(request, pk, template_name="restaurants/form.html")


# 6-1. 음식점 수정 (edit 별칭 URL)
@login_required
def restaurant_edit(request, pk):
    # edit URL도 update 폼을 사용하도록 통일
    return _restaurant_update_impl(request, pk, template_name="restaurants/form.html")


def _restaurant_update_impl(request, pk, template_name: str):
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # 사장(owner) 또는 관리자(staff/superuser)만 수정 가능
    if not (request.user == restaurant.owner or request.user.is_staff or request.user.is_superuser):
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("restaurants:detail", pk=pk)

    if request.method == "POST":
        # 기본 필드 업데이트
        restaurant.name = request.POST.get("name", "").strip()
        restaurant.address = request.POST.get("address", "").strip()
        restaurant.phone = request.POST.get("phone", "").strip()
        restaurant.description = request.POST.get("description", "").strip()
        restaurant.hours = request.POST.get("hours", "").strip()
        restaurant.closed_days = request.POST.get("closed_days", "").strip()
        restaurant.website = request.POST.get("website", "").strip()

        # 카테고리 업데이트
        category_pk = request.POST.get("category")
        if category_pk:
            restaurant.category_id = category_pk

        # 대표 사진 변경 시
        if request.FILES.get("thumbnail"):
            restaurant.thumbnail = request.FILES.get("thumbnail")

        # 좌표 초기화 및 저장
        restaurant.lat, restaurant.lng = None, None
        restaurant.save()

        # 상세 사진 추가 등록 (최대 10장까지) - update 템플릿에서만 사용될 수 있음
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
    return render(request, template_name, {"mode": "update", "restaurant": restaurant, "categories": categories, "form_data": _extract_form_data(request.POST), "current_registered": restaurant.additional_images.count()})
