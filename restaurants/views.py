from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Restaurant, Category

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

    context = {
        "restaurants": qs, 
        "q": q, 
        "categories": Category.objects.all(), 
        "category_id": category_id, 
        "sort": sort
    }
    return render(request, "restaurants/list.html", context)

# 2. 음식점 상세 (리뷰 정렬 및 소수점 처리 반영)
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
    
    # --- [리뷰 정렬 로직 추가] ---
    sort = request.GET.get('sort', 'rating_high')  # 기본값: 별점 높은 순
    reviews_qs = restaurant.reviews.select_related("author")

    if sort == 'latest':
        reviews = reviews_qs.order_by("-created_at")
    elif sort == 'rating_low':
        reviews = reviews_qs.order_by("rating", "-created_at")
    else:  # rating_high
        reviews = reviews_qs.order_by("-rating", "-created_at")
    # ---------------------------

    # 별점 분포 계산
    rating_distribution = []
    total = reviews_qs.count()
    for star in range(5, 0, -1):
        count = reviews_qs.filter(rating=star).count()
        pct = (count / total * 100) if total > 0 else 0
        rating_distribution.append((star, count, round(pct)))

    # 즐겨찾기 여부
    is_favorite = False
    if request.user.is_authenticated:
        try:
            from favorites.models import Favorite
            is_favorite = Favorite.objects.filter(user=request.user, restaurant=restaurant).exists()
        except: 
            pass

    context = {
        "restaurant": restaurant, 
        "reviews": reviews, 
        # 소수점 1자리(혹은 2자리) 반올림 처리
        "avg_rating": round(restaurant.avg_rating, 1) if restaurant.avg_rating else None, 
        "rating_distribution": rating_distribution, 
        "is_favorite": is_favorite,
        "current_sort": sort,
    }
    return render(request, "restaurants/detail.html", context)


# 3. 음식점 등록
@login_required
def restaurant_create(request):
    if not request.user.is_staff:
        messages.error(request, "권한이 없습니다.")
        return redirect("/restaurants/")

    # DB에 카테고리가 없다면 자동 생성
    if not Category.objects.exists():
        default_categories = ['한식', '중식', '일식', '양식', '카페', '패스트푸드', '기타']
        for cat_name in default_categories:
            Category.objects.create(name=cat_name)

    categories = Category.objects.all()

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category_pk = request.POST.get("category", "").strip()
        address = request.POST.get("address", "").strip()

        if not name or not address:
            messages.error(request, "필수 항목을 입력해주세요.")
            return render(request, "restaurants/create.html", {"categories": categories, "form_data": request.POST})

        # 조원 코드의 필드명(owner, thumbnail 등) 유지
        restaurant = Restaurant(
            owner=request.user, 
            name=name, 
            address=address,
            phone=request.POST.get("phone", "").strip(),
            description=request.POST.get("description", "").strip(),
            hours=request.POST.get("hours", "").strip(),
            closed_days=request.POST.get("closed_days", "").strip(),
            website=request.POST.get("website", "").strip(),
            thumbnail=request.FILES.get("thumbnail") # image 대신 thumbnail 사용 확인
        )

        if category_pk and category_pk.isdigit():
            restaurant.category = Category.objects.filter(pk=category_pk).first()
        else:
            try:
                restaurant.category = Category.objects.get(name=category_pk)
            except:
                pass
        
        restaurant.save()
        messages.success(request, f'"{name}" 등록 성공! 🎉')

        try: 
            return redirect(f"/restaurants/{restaurant.pk}/")
        except: 
            return redirect("/restaurants/")

    return render(request, "restaurants/create.html", {"categories": categories, "form_data": {}})

# 4. 지도 페이지
def restaurant_map(request):
    return render(request, 'Maps_Api.html', {'restaurants': Restaurant.objects.all()})