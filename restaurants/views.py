from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Restaurant, Category, RestaurantImage, Tag, RestaurantTag, MenuItem

import os
import environ

# 메인 브랜치의 설정과 feature 브랜치의 environ 설정을 통합
env = environ.Env()
env_file = os.path.join(settings.BASE_DIR, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

def _extract_form_data(post):
    """기존 팀원이 만든 폼 데이터 추출 함수 유지"""
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

# 태그명 → 카테고리명 매핑 (식당에 태그 미할당 시 카테고리 폴백)
TAG_CATEGORY_MAP = {
    '데이트':   ['카페', '양식'],
    '혼밥':     ['한식', '일식', '분식'],
    '회식':     ['한식', '중식'],
    '뷰맛집':   ['카페'],
    '가족모임': ['한식'],
    '반려동물': ['카페', '기타'],
    '주차가능': ['한식', '중식', '양식'],
    '채식':     ['기타'],
}

def restaurant_list(request):
    q = request.GET.get("q", "")
    sort = request.GET.get("sort", "latest")
    category_id = request.GET.get("category", "")
    tag_id = request.GET.get("tag", "")
    min_rating = request.GET.get("min_rating", "")
    price_range_filter = request.GET.get("price_range", "")

    # avg_rating은 모델 @property이므로 annotate 이름 충돌 방지 위해 _sort_rating 사용
    restaurants = Restaurant.objects.all().annotate(
        review_count=Count('reviews', distinct=True),
        _sort_rating=Avg('reviews__rating'),
    )

    if q:
        restaurants = restaurants.filter(
            Q(name__icontains=q) | Q(category__name__icontains=q) | Q(address__icontains=q)
        )

    if category_id:
        restaurants = restaurants.filter(category_id=category_id)

    if min_rating:
        try:
            restaurants = restaurants.filter(_sort_rating__gte=float(min_rating))
        except ValueError:
            pass

    if price_range_filter:
        restaurants = restaurants.filter(price_range=price_range_filter)

    if tag_id:
        # 1) 직접 태그 필터
        tagged = restaurants.filter(tags__id=tag_id)
        if tagged.exists():
            restaurants = tagged
        else:
            # 2) 태그에 연결된 식당이 없으면 카테고리 매핑으로 폴백
            tag_obj = Tag.objects.filter(id=tag_id).first()
            if tag_obj:
                cat_names = TAG_CATEGORY_MAP.get(tag_obj.name, [])
                if cat_names:
                    restaurants = restaurants.filter(category__name__in=cat_names)

    if sort == "rating":
        restaurants = restaurants.order_by("-_sort_rating", "-id")
    elif sort == "views":
        restaurants = restaurants.order_by("-view_count", "-id")
    else:
        restaurants = restaurants.order_by("-id")

    categories = Category.objects.all()
    tags = Tag.objects.all()

    user_favorites = set()
    if request.user.is_authenticated:
        user_favorites = set(
            request.user.favorites.values_list("restaurant_id", flat=True)
        )

    # 페이지네이션 (12개/페이지)
    paginator = Paginator(restaurants, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "restaurants/list.html", {
        "restaurants": page_obj,       # 템플릿에서 그대로 사용
        "page_obj": page_obj,
        "total_count": paginator.count,
        "q": q,
        "sort": sort,
        "category_id": category_id,
        "tag_id": tag_id,
        "categories": categories,
        "tags": tags,
        "user_favorites": user_favorites,
        "min_rating": min_rating,
        "price_range_filter": price_range_filter,
        "price_range_choices": [
            ('cheap',   '1만원 이하'),
            ('mid',     '1~2만원'),
            ('high',    '2~3만원'),
            ('premium', '3만원 이상'),
        ],
    })

def restaurant_map(request):
    """지도 탐색 뷰 - 초기 렌더링용 (카테고리 목록 전달)"""
    categories = Category.objects.all()
    naver_client_id = settings.NAVER_CLIENT_ID
    return render(request, "Maps_API.html", {
        "categories": categories,
        "naver_client_id": naver_client_id,
    })


def restaurant_map_api(request):
    """지도 영역 + 검색어 기반 AJAX API - JSON 반환"""
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()

    # 지도 bounds (남서 ~ 북동)
    try:
        sw_lat = float(request.GET.get("sw_lat", 33.0))
        sw_lng = float(request.GET.get("sw_lng", 124.0))
        ne_lat = float(request.GET.get("ne_lat", 38.9))
        ne_lng = float(request.GET.get("ne_lng", 132.0))
    except (ValueError, TypeError):
        sw_lat, sw_lng, ne_lat, ne_lng = 33.0, 124.0, 38.9, 132.0

    qs = (
        Restaurant.objects
        .exclude(lat__isnull=True)
        .exclude(lng__isnull=True)
        .select_related("category")
        .annotate(avg_r=Avg("reviews__rating"), review_cnt=Count("reviews"))
    )

    # 지도 영역 필터
    qs = qs.filter(
        lat__gte=sw_lat, lat__lte=ne_lat,
        lng__gte=sw_lng, lng__lte=ne_lng,
    )

    # 검색어 필터
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(category__name__icontains=q)
            | Q(address__icontains=q)
        )

    # 카테고리 필터
    if category_id:
        qs = qs.filter(category_id=category_id)

    # 최대 100개 반환
    qs = qs[:100]

    data = []
    for r in qs:
        thumbnail_url = ""
        if r.thumbnail:
            thumbnail_url = request.build_absolute_uri(r.thumbnail.url)
        data.append({
            "id": r.id,
            "name": r.name,
            "category": r.category.name if r.category else "",
            "address": r.address,
            "lat": float(r.lat),
            "lng": float(r.lng),
            "avg_rating": round(r.avg_r, 1) if r.avg_r else 0,
            "review_count": r.review_cnt or 0,
            "thumbnail": thumbnail_url,
            "detail_url": f"/restaurants/{r.id}/",
        })

    return JsonResponse({"restaurants": data})

def restaurant_detail(request, pk):
    """상세 페이지 뷰"""
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # ✅ 병합 1: 조회수 증가 로직 유지 (main 브랜치 내용)
    restaurant.view_count += 1
    restaurant.save()

    # ✅ 병합 2: 정렬 처리 로직 유지 (hyunsang-1 브랜치 내용)
    sort = request.GET.get('sort', 'rating_high')
    all_reviews = restaurant.reviews.all()
    if sort == 'latest':
        reviews = all_reviews.order_by('-created_at')
    elif sort == 'rating_low':
        reviews = all_reviews.order_by('rating', '-created_at')
    else:
        reviews = all_reviews.order_by('-rating', '-created_at')

    total_reviews = all_reviews.count()
    
    rating_distribution = []
    for i in range(5, 0, -1):
        count = all_reviews.filter(rating=i).count()
        pct = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_distribution.append({"star": i, "count": count, "pct": int(pct)})
    
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = restaurant.favorited_by.filter(user=request.user).exists()

    # 메뉴 아이템 (카테고리별 그룹)
    menu_items = restaurant.menu_items.filter(is_available=True)
    menu_by_category = {}
    for item in menu_items:
        cat_label = dict(MenuItem.CATEGORY_CHOICES).get(item.category, item.category)
        menu_by_category.setdefault(cat_label, []).append(item)

    # 좋아요 누른 리뷰 ID 목록
    liked_review_ids = set()
    if request.user.is_authenticated:
        from reviews.models import ReviewLike
        liked_review_ids = set(
            ReviewLike.objects.filter(user=request.user, review__restaurant=restaurant)
            .values_list('review_id', flat=True)
        )

    # 근처 맛집 (반경 약 2km)
    nearby = []
    if restaurant.lat and restaurant.lng:
        nearby = list(
            Restaurant.objects
            .exclude(pk=restaurant.pk)
            .filter(
                lat__range=(float(restaurant.lat) - 0.018, float(restaurant.lat) + 0.018),
                lng__range=(float(restaurant.lng) - 0.022, float(restaurant.lng) + 0.022),
            )
            .annotate(review_count=Count('reviews', distinct=True))
            .select_related('category')
            .order_by('-view_count')[:5]
        )

    context = {
        "restaurant": restaurant,
        "reviews": reviews,
        "rating_distribution": rating_distribution,
        "current_sort": sort,
        "is_favorite": is_favorite,
        "MAP_API_KEY": settings.NAVER_CLIENT_ID,
        "menu_by_category": menu_by_category,
        "all_menu_items": menu_items,
        "tags": restaurant.tags.all(),
        "liked_review_ids": liked_review_ids,
        "nearby": nearby,
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
            # ✅ 누락됐던 브레이크 타임 저장 복구!
            break_time=request.POST.get("break_time", "").strip(),
            closed_days=request.POST.get("closed_days", "").strip(),
            website=request.POST.get("website", "").strip(),
            thumbnail=request.FILES.get("thumbnail"),
            price_range=request.POST.get("price_range", "").strip(),
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
        
        # ✅ 누락됐던 브레이크 타임 수정 복구!
        restaurant.break_time = request.POST.get("break_time", "").strip()
        
        restaurant.closed_days = request.POST.get("closed_days", "").strip()
        restaurant.website = request.POST.get("website", "").strip()
        restaurant.price_range = request.POST.get("price_range", "").strip()

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


# ────────────────────────────────────────────────
# 자동완성 API
# ────────────────────────────────────────────────
def restaurant_autocomplete(request):
    """검색어 자동완성 – 최대 8개 JSON 반환"""
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse({'results': []})
    qs = (
        Restaurant.objects
        .filter(Q(name__icontains=q) | Q(category__name__icontains=q) | Q(address__icontains=q))
        .select_related('category')
        .order_by('-view_count')[:8]
    )
    data = [
        {
            'id': r.id,
            'name': r.name,
            'category': r.category.name if r.category else '',
            'address': (r.address or '')[:25],
        }
        for r in qs
    ]
    return JsonResponse({'results': data})


# ────────────────────────────────────────────────
# 베스트 랭킹 페이지
# ────────────────────────────────────────────────
def restaurant_ranking(request):
    """별점·리뷰수 기반 TOP 50 랭킹"""
    restaurants = (
        Restaurant.objects
        .annotate(
            review_count=Count('reviews', distinct=True),
            avg_r=Avg('reviews__rating'),
        )
        .filter(review_count__gte=1)
        .order_by('-avg_r', '-review_count', '-view_count')
        .select_related('category')[:50]
    )
    return render(request, 'restaurants/ranking.html', {'restaurants': restaurants})


# ────────────────────────────────────────────────
# 메뉴 CRUD (사장 전용)
# ────────────────────────────────────────────────
@login_required
def menu_item_create(request, pk):
    """메뉴 아이템 추가"""
    restaurant = get_object_or_404(Restaurant, pk=pk)
    if not (restaurant.owner == request.user or request.user.is_staff):
        messages.error(request, "권한이 없습니다.")
        return redirect("restaurants:detail", pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        price_raw = request.POST.get("price", "0").strip().replace(",", "")
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "main")
        image = request.FILES.get("image")

        try:
            price = int(price_raw)
        except ValueError:
            price = 0

        if name:
            MenuItem.objects.create(
                restaurant=restaurant,
                name=name,
                price=price,
                description=description,
                category=category,
                image=image,
                is_available=True,
            )
            messages.success(request, f"'{name}' 메뉴가 추가됐어요!")
        else:
            messages.error(request, "메뉴 이름을 입력해주세요.")

    return redirect("restaurants:detail", pk=pk)


@login_required
def menu_item_update(request, pk, item_pk):
    """메뉴 아이템 수정"""
    restaurant = get_object_or_404(Restaurant, pk=pk)
    item = get_object_or_404(MenuItem, pk=item_pk, restaurant=restaurant)

    if not (restaurant.owner == request.user or request.user.is_staff):
        messages.error(request, "권한이 없습니다.")
        return redirect("restaurants:detail", pk=pk)

    if request.method == "POST":
        item.name = request.POST.get("name", item.name).strip()
        price_raw = request.POST.get("price", str(item.price)).strip().replace(",", "")
        item.description = request.POST.get("description", item.description).strip()
        item.category = request.POST.get("category", item.category)
        item.is_available = request.POST.get("is_available") == "on"

        try:
            item.price = int(price_raw)
        except ValueError:
            pass

        if request.FILES.get("image"):
            item.image = request.FILES.get("image")

        item.save()
        messages.success(request, "메뉴가 수정됐어요!")

    return redirect("restaurants:detail", pk=pk)


@login_required
def menu_item_delete(request, pk, item_pk):
    """메뉴 아이템 삭제"""
    restaurant = get_object_or_404(Restaurant, pk=pk)
    item = get_object_or_404(MenuItem, pk=item_pk, restaurant=restaurant)

    if not (restaurant.owner == request.user or request.user.is_staff):
        messages.error(request, "권한이 없습니다.")
        return redirect("restaurants:detail", pk=pk)

    if request.method == "POST":
        item.delete()
        messages.success(request, "메뉴가 삭제됐어요.")

    return redirect("restaurants:detail", pk=pk)


# ────────────────────────────────────────────────
# 태그 토글 (AJAX, 사장 전용)
# ────────────────────────────────────────────────
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def restaurant_tag_toggle(request, pk, tag_pk):
    """태그 추가/제거 토글 (AJAX)"""
    from django.http import JsonResponse
    restaurant = get_object_or_404(Restaurant, pk=pk)

    if not (restaurant.owner == request.user or request.user.is_staff):
        return JsonResponse({"error": "권한이 없습니다."}, status=403)

    tag = get_object_or_404(Tag, pk=tag_pk)
    rt, created = RestaurantTag.objects.get_or_create(restaurant=restaurant, tag=tag)
    if not created:
        rt.delete()
        added = False
    else:
        added = True

    return JsonResponse({"added": added, "tag": tag.name})