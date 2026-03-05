from django.shortcuts import render

def home(request):
<<<<<<< Updated upstream
    return render(request, 'home.html')
=======
    from restaurants.models import Restaurant, Tag, Category
    from reviews.models import Review
    from django.contrib.auth import get_user_model
    from django.db.models import Max
    from .models import FoodStory
    User = get_user_model()

    # 인기 맛집 = 평점 × 리뷰수 복합 점수 (리뷰 없는 식당 제외)
    featured = list(
        Restaurant.objects
        .annotate(
            review_count=Count('reviews', distinct=True),
            avg_r=Avg('reviews__rating'),
        )
        .filter(review_count__gte=1)
        .annotate(
            pop_score=ExpressionWrapper(
                F('avg_r') * F('review_count'),
                output_field=FloatField()
            )
        )
        .order_by('-pop_score', '-review_count', '-id')[:8]
    )

    # 식당별 최신 리뷰 1개씩 (중복 식당 방지)
    latest_ids = list(
        Review.objects
        .values('restaurant')
        .annotate(latest=Max('id'))
        .values_list('latest', flat=True)
        .order_by('-latest')[:8]
    )
    recent_reviews = (
        Review.objects
        .filter(id__in=latest_ids)
        .select_related('restaurant', 'author')
        .order_by('-id')
    )

    food_stories = FoodStory.objects.filter(is_published=True)[:8]

    # 테마별 맛집: 카테고리 기반으로 각 테마마다 다른 식당 표시
    THEMES = [
        {"label": "데이트 코스", "desc": "분위기 좋은 둘만의 장소",    "categories": ["카페", "양식"],  "start": 0, "order": "-view_count", "limit": 4},
        {"label": "혼밥 맛집",   "desc": "혼자 편하게 즐기기 좋아요", "categories": ["한식", "일식"],  "start": 0, "order": "-view_count", "limit": 4},
        {"label": "회식 장소",   "desc": "단체 모임에 딱 좋은 곳",    "categories": ["한식", "중식"],  "start": 4, "order": "-view_count", "limit": 4},
    ]
    theme_sections = []
    for t in THEMES:
        cat_objs = Category.objects.filter(name__in=t["categories"])
        s, e = t["start"], t["start"] + t["limit"]
        rs = list(
            Restaurant.objects
            .filter(category__in=cat_objs)
            .annotate(
                review_count=Count('reviews', distinct=True),
            )
            .order_by(t["order"], '-id')
            .select_related('category')[s:e]
        )
        if not rs:
            rs = list(
                Restaurant.objects
                .annotate(
                    review_count=Count('reviews', distinct=True),
                )
                .order_by('-view_count', '-id')
                .select_related('category')[s:e]
            )
        link = f"/restaurants/?category={cat_objs.first().pk}" if cat_objs.exists() else "/restaurants/"
        theme_sections.append({
            "label": t["label"], "desc": t["desc"],
            "restaurants": rs,
            "link": link,
        })

    context = {
        'featured_restaurants': featured,
        'restaurant_count': Restaurant.objects.count(),
        'review_count':     Review.objects.count(),
        'user_count':       User.objects.count(),
        'recent_reviews':   recent_reviews,
        'theme_sections':   theme_sections,
        'food_stories':     food_stories,
        'ai_suggestions': [
            '데이트하기 좋은 분위기 맛집',
            '혼밥하기 편한 한식당',
            '단체 회식 장소 추천',
            '경치 좋은 뷰 맛집',
            '가성비 좋은 점심 맛집',
        ],
    }
    return render(request, 'home.html', context)


# ── 알림 읽음 처리 ────────────────────────────────────────
@login_required
@require_POST
def notification_read(request, pk):
    from .models import Notification
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({"ok": True})
>>>>>>> Stashed changes
