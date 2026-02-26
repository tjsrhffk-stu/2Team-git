from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Restaurant, Category


def _is_owner_user(user) -> bool:
    try:
        return user.is_authenticated and hasattr(user, "profile") and user.profile.user_type == "OWNER"
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

    if sort == "rating":
        qs = qs.order_by("-avg_rating", "-review_count", "-id")
    elif sort == "reviews":
        qs = qs.order_by("-review_count", "-id")
    elif sort == "views":
        qs = qs.order_by("-view_count", "-id")
    else:
        qs = qs.order_by("-id")

    user_favorites = []
    if request.user.is_authenticated:
        try:
            from favorites.models import Favorite
            user_favorites = Favorite.objects.filter(user=request.user).values_list('restaurant_id', flat=True)
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

    sort = request.GET.get('sort', 'rating_high')
    reviews_qs = restaurant.reviews.select_related("author")

    if sort == 'latest':
        reviews = reviews_qs.order_by("-created_at")
    elif sort == 'rating_low':
        reviews = reviews_qs.order_by("rating", "-created_at")
    else:
        reviews = reviews_qs.order_by("-rating", "-created_at")

    rating_distribution = []
    total = reviews_qs.count()
    for star in range(5, 0, -1):
        count = reviews_qs.filter(rating=star).count()
        pct = (count / total * 100) if total > 0 else 0
        rating_distribution.append((star, count, round(pct)))

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
    }
    return render(request, "restaurants/detail.html", context)


# 3. 음식점 등록 (사장만)
@login_required
def restaurant_create(request):
    if not _is_owner_user(request.user):
        messages.error(request, "사장님 계정만 식당 등록이 가능합니다.")
        return redirect("/restaurants/")

    if not Category.objects.exists():
        default_categories = ['한식', '중식', '일식', '양식', '카페', '패스트푸드', '기타']
        for cat_name in default_categories:
            Category.objects.get_or_create(name=cat_name)

    categories = Category.objects.all()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_input = request.POST.get("category", "").strip()
        address = request.POST.get("address", "").strip()

        if not name or not address:
            messages.error(request, "필수 항목을 입력해주세요.")
            return render(request, "restaurants/create.html", {"categories": categories, "form_data": request.POST})

        restaurant = Restaurant(
            owner=request.user,
            name=name,
            address=address,
            phone=request.POST.get("phone", "").strip(),
            description=request.POST.get("description", "").strip(),
            hours=request.POST.get("hours", "").strip(),
            closed_days=request.POST.get("closed_days", "").strip(),
            website=request.POST.get("website", "").strip(),
            thumbnail=request.FILES.get("thumbnail")
        )

        if category_input:
            if category_input.isdigit():
                restaurant.category = Category.objects.filter(pk=category_input).first()
            else:
                restaurant.category = Category.objects.filter(name=category_input).first()

        restaurant.save()
        messages.success(request, f'"{name}" 등록 성공! 🎉')
        return redirect(f"/restaurants/{restaurant.pk}/")

    return render(request, "restaurants/create.html", {"categories": categories, "form_data": {}})


# ✅ 4. 음식점 수정 (사장 + 내 소유 식당만)
@login_required
def restaurant_edit(request, pk):
    if not _is_owner_user(request.user):
        messages.error(request, "사장님 계정만 수정이 가능합니다.")
        return redirect("/restaurants/")

    restaurant = get_object_or_404(Restaurant, pk=pk)

    if restaurant.owner_id != request.user.id:
        messages.error(request, "내가 등록한 식당만 수정할 수 있어요.")
        return redirect(f"/restaurants/{restaurant.pk}/")

    categories = Category.objects.all()

    if request.method == "POST":
        restaurant.name = request.POST.get("name", "").strip()
        category_input = request.POST.get("category", "").strip()
        restaurant.address = request.POST.get("address", "").strip()
        restaurant.phone = request.POST.get("phone", "").strip()
        restaurant.description = request.POST.get("description", "").strip()
        restaurant.hours = request.POST.get("hours", "").strip()
        restaurant.closed_days = request.POST.get("closed_days", "").strip()
        restaurant.website = request.POST.get("website", "").strip()

        thumb = request.FILES.get("thumbnail")
        if thumb:
            restaurant.thumbnail = thumb

        if not restaurant.name or not restaurant.address:
            messages.error(request, "필수 항목을 입력해주세요.")
            return render(
                request,
                "restaurants/edit.html",
                {"restaurant": restaurant, "categories": categories}
            )

        if category_input:
            if category_input.isdigit():
                restaurant.category = Category.objects.filter(pk=category_input).first()
            else:
                restaurant.category = Category.objects.filter(name=category_input).first()

        restaurant.save()
        messages.success(request, "수정이 완료됐어요 ✅")
        return redirect(f"/restaurants/{restaurant.pk}/")

    return render(request, "restaurants/edit.html", {"restaurant": restaurant, "categories": categories})


# ✅ 5. 음식점 삭제 (사장 + 내 소유 식당만)
@login_required
def restaurant_delete(request, pk):
    if not _is_owner_user(request.user):
        messages.error(request, "사장님 계정만 삭제가 가능합니다.")
        return redirect("/restaurants/")

    restaurant = get_object_or_404(Restaurant, pk=pk)

    if restaurant.owner_id != request.user.id:
        messages.error(request, "내가 등록한 식당만 삭제할 수 있어요.")
        return redirect(f"/restaurants/{restaurant.pk}/")

    if request.method == "POST":
        name = restaurant.name
        restaurant.delete()
        messages.success(request, f'"{name}" 삭제 완료 🗑️')
        return redirect("/users/mypage/")

    return render(request, "restaurants/confirm_delete.html", {"restaurant": restaurant})


# 6. 지도 페이지
def restaurant_map(request):
    return render(request, 'Maps_Api.html', {'restaurants': Restaurant.objects.all()})