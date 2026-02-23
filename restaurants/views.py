from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Restaurant, Category


# 음식점 목록
def restaurant_list(request):
    q           = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    sort        = request.GET.get("sort", "latest")  # latest | rating | reviews | views

    qs = Restaurant.objects.all().annotate(
        avg_rating=Avg("reviews__rating"),
        review_count=Count("reviews"),
    )

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q))

    if category_id:
        # 이름으로 필터 (카테고리가 문자열로 넘어오는 경우)
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

    categories = Category.objects.all()

    context = {
        "restaurants": qs,
        "q": q,
        "categories": categories,
        "category_id": category_id,
        "sort": sort,
    }
    return render(request, "restaurants/list.html", context)


# 음식점 상세
def restaurant_detail(request, pk):
    restaurant = get_object_or_404(
        Restaurant.objects.annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews"),
        ),
        pk=pk,
    )

    # 조회수 증가
    Restaurant.objects.filter(pk=pk).update(view_count=restaurant.view_count + 1)

    # 리뷰 목록
    reviews = restaurant.reviews.select_related("author").order_by("-created_at")

    # 별점 분포 계산 (5점 → 1점 순서)
    rating_distribution = []
    total = reviews.count()
    for star in range(5, 0, -1):
        count = reviews.filter(rating=star).count()
        pct = (count / total * 100) if total > 0 else 0
        rating_distribution.append((star, count, round(pct)))

    # 즐겨찾기 여부
    is_favorite = False
    if request.user.is_authenticated:
        try:
            from favorites.models import Favorite
            is_favorite = Favorite.objects.filter(
                user=request.user, restaurant=restaurant
            ).exists()
        except Exception:
            pass

    context = {
        "restaurant": restaurant,
        "reviews": reviews,
        "avg_rating": round(restaurant.avg_rating, 1) if restaurant.avg_rating else None,
        "rating_distribution": rating_distribution,
        "is_favorite": is_favorite,
    }
    return render(request, "restaurants/detail.html", context)


# 음식점 등록
@login_required
def restaurant_create(request):
    categories = Category.objects.all()

    if request.method == "POST":
        name        = request.POST.get("name", "").strip()
        category_id = request.POST.get("category", "")
        address     = request.POST.get("address", "").strip()
        phone       = request.POST.get("phone", "").strip()
        description = request.POST.get("description", "").strip()
        hours       = request.POST.get("hours", "").strip()
        closed_days = request.POST.get("closed_days", "").strip()
        website     = request.POST.get("website", "").strip()
        image       = request.FILES.get("image")

        # 유효성 검사
        if not name or not address:
            messages.error(request, "음식점 이름과 주소는 필수예요.")
            return render(request, "restaurants/create.html", {
                "categories": categories,
                "form": request.POST,
            })

        restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            description=description,
            hours=hours,
            website=website,
        )

        if category_id:
            try:
                restaurant.category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                pass

        if image:
            restaurant.image = image

        restaurant.save()
        messages.success(request, f'"{name}" 음식점이 등록되었어요! 🎉')
        return redirect("restaurants:detail", pk=restaurant.pk)

    return render(request, "restaurants/create.html", {
        "categories": categories,
        "form": {},
    })