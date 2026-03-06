from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Case, When, IntegerField, Avg, FloatField, ExpressionWrapper, F


# ──────────────────────────────────────────────
# 확장 키워드 매핑
# ──────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    '한식': [
        '한식', '한국', '불고기', '된장', '김치', '삼겹살', '갈비', '비빔밥',
        '설렁탕', '순두부', '냉면', '국밥', '칼국수', '순대국', '해장국',
        '삼계탕', '보쌈', '족발', '곱창', '대창', '막창', '갈비탕',
        '부대찌개', '김치찌개', '된장찌개', '제육볶음', '낙지볶음',
        '한정식', '백반', '밥집', '국밥집', '고깃집',
    ],
    '일식': [
        '일식', '일본', '초밥', '스시', '라멘', '우동', '소바', '돈카츠',
        '야키토리', '오마카세', '타코야키', '오니기리', '사시미', '회집', '회뜨기',
        '일본요리', '덮밥', '가츠동', '규동', '텐동',
    ],
    '중식': [
        '중식', '중국', '짜장', '짜장면', '짬뽕', '탕수육', '마라', '마라탕',
        '딤섬', '양꼬치', '꼬치', '중화', '완탕', '중국요리', '볶음밥',
    ],
    '양식': [
        '양식', '파스타', '피자', '스테이크', '리조또', '버거', '햄버거',
        '샐러드', '브런치', '프렌치', '이탈리안', '그릴', '오븐',
        '레스토랑', '다이닝', '파인다이닝', '양식당', '경양식',
    ],
    '카페': [
        '카페', '커피', '디저트', '케이크', '아이스크림', '베이커리',
        '티', '라떼', '에스프레소', '아메리카노', '카푸치노',
        '브런치 카페', '루프탑 카페', '감성 카페', '스터디 카페',
    ],
    '분식': [
        '분식', '떡볶이', '순대', '어묵', '튀김', '김밥',
        '라볶이', '치즈 떡볶이',
    ],
    '패스트푸드': [
        '패스트푸드', '버거', '치킨', '핫도그', '햄버거', '수제버거',
        '치즈버거', '패티', '프라이드치킨',
    ],
    '기타': [
        '베트남', '태국', '인도', '멕시칸', '쌀국수', '팟타이',
        '커리', '나시고렝', '월남쌈', '분짜',
    ],
}

TAG_KEYWORDS = {
    '데이트': ['데이트', '로맨틱', '커플', '둘이', '기념일', '분위기 좋은', '분위기있는'],
    '혼밥':   ['혼밥', '혼자', '1인', '혼술', '솔로', '혼자서', '나 혼자'],
    '회식':   ['회식', '단체', '모임', '회사', '단체석', '회식 장소', '단체 예약'],
    '뷰맛집': ['뷰', '경치', '야경', '전망', '루프탑', '한강뷰', '뷰 맛집', '경치 좋은'],
    '가족모임': ['가족', '어른', '어르신', '아이', '아기', '어린이', '가족 모임'],
}

# 가성비 / 분위기 / 시간대 힌트 키워드 (설명 검색용)
EXTRA_KEYWORDS = {
    '가성비': ['가성비', '저렴', '착한 가격', '합리적', '싼', '경제적', '저가'],
    '점심':   ['점심', '런치', '점심 특선', '점심 메뉴', '브런치'],
    '저녁':   ['저녁', '디너', '야식', '밤'],
    '전통':   ['전통', '오래된', '역사', '노포', '할머니'],
    '신선':   ['신선', '제철', '국내산', '유기농'],
    '고급':   ['고급', '파인다이닝', '특별한', '럭셔리', '프리미엄'],
}


def _parse_query(query):
    """쿼리에서 카테고리, 태그, 추가 힌트 키워드를 추출"""
    q = query.lower()

    matched_categories = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in q for kw in kws):
            matched_categories.append(cat)

    matched_tags = []
    for tag, kws in TAG_KEYWORDS.items():
        if any(kw in q for kw in kws):
            matched_tags.append(tag)

    hint_keywords = []
    for _, kws in EXTRA_KEYWORDS.items():
        for kw in kws:
            if kw in q:
                hint_keywords.append(kw)

    return matched_categories, matched_tags, hint_keywords


# ──────────────────────────────────────────────
# AI 검색 뷰  (OR 기반 스마트 랭킹)
# ──────────────────────────────────────────────
def ai_search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return redirect('restaurants:list')

    from restaurants.models import Restaurant, Category, Tag

    matched_categories, matched_tags, hint_keywords = _parse_query(query)

    base_qs = Restaurant.objects.annotate(
        review_count=Count('reviews', distinct=True),
    ).select_related('category')

    # ── 1단계: 카테고리 필터 (OR) ──────────────────
    if matched_categories:
        cat_objs = Category.objects.filter(name__in=matched_categories)
        qs = base_qs.filter(category__in=cat_objs)
    else:
        qs = base_qs.all()

    # ── 2단계: 태그 OR 설명 텍스트 필터로 우선순위 점수 부여 ──
    # 태그가 있는 레스토랑을 먼저 보여주되 없어도 제외하지 않음
    tag_objs = Tag.objects.filter(name__in=matched_tags) if matched_tags else Tag.objects.none()

    # 연관 설명 키워드 Q 객체
    desc_q = Q()
    for kw in hint_keywords:
        desc_q |= Q(description__icontains=kw)
    for kw in hint_keywords:
        desc_q |= Q(name__icontains=kw)

    # 관련성 점수: 태그 일치 +2 / 설명 힌트 일치 +1
    qs = qs.annotate(
        tag_score=Case(
            When(tags__in=tag_objs, then=2) if tag_objs.exists() else When(pk__isnull=True, then=0),
            default=0,
            output_field=IntegerField(),
        ),
    ).distinct()

    # ── 3단계: 카테고리도 없고 태그도 없으면 → 전체 텍스트 검색 ──
    if not matched_categories and not matched_tags and not hint_keywords:
        text_q = (
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(address__icontains=query) |
            Q(category__name__icontains=query)
        )
        qs = base_qs.filter(text_q).distinct()

    # ── 4단계: 결과 정렬 (관련성 → 리뷰 수 → 최신) ──
    # 텍스트 검색 폴백일 때는 tag_score 어노테이션이 없으므로 분기 처리
    if matched_categories or matched_tags or hint_keywords:
        qs = qs.order_by('-tag_score', '-review_count', '-id')
    else:
        qs = qs.order_by('-review_count', '-id')

    # ── 5단계: 결과 없으면 전체 인기순 폴백 ──
    is_fallback = False
    if not qs.exists():
        qs = base_qs.order_by('-review_count', '-id')
        is_fallback = True

    total_count = qs.count()

    # ── 6단계: 페이지네이션 (12개/페이지) ──
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/ai_search.html', {
        'query': query,
        'restaurants': page_obj,
        'page_obj': page_obj,
        'matched_categories': matched_categories,
        'matched_tags': matched_tags,
        'hint_keywords': hint_keywords,
        'result_count': total_count,
        'is_fallback': is_fallback,
        'matched_category': matched_categories[0] if matched_categories else None,
    })


# ──────────────────────────────────────────────
# 홈 뷰
# ──────────────────────────────────────────────
def home(request):
    from restaurants.models import Restaurant, Tag, Category
    from reviews.models import Review
    from django.contrib.auth import get_user_model
    from django.db.models import Max
    from .models import FoodStory
    User = get_user_model()

    # 인기 맛집 = 평점 × 리뷰수 복합 점수 (리뷰 없는 식당 제외)
    featured = (
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
        .order_by('-pop_score', '-review_count', '-id')[:6]
    )

    # 식당별 최신 리뷰 1개씩 (중복 식당 방지)
    latest_ids = (
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
        {"label": "데이트 코스", "desc": "분위기 좋은 둘만의 장소",    "categories": ["카페", "양식"],        "start": 0, "order": "-view_count"},
        {"label": "혼밥 맛집",   "desc": "혼자 편하게 즐기기 좋아요", "categories": ["한식", "일식"],        "start": 0, "order": "-view_count"},
        {"label": "회식 장소",   "desc": "단체 모임에 딱 좋은 곳",    "categories": ["한식", "중식"],        "start": 4, "order": "-view_count"},
        {"label": "뷰 맛집",     "desc": "맛도 경치도 두 배 행복",    "categories": ["카페", "기타"],        "start": 4, "order": "-id"},
        {"label": "가족 모임",   "desc": "온 가족이 함께하기 좋은 곳", "categories": ["한식", "양식"],       "start": 4, "order": "-id"},
        {"label": "가성비 맛집", "desc": "부담없이 즐기는 알짜 맛집",  "categories": ["분식", "패스트푸드"], "start": 0, "order": "-view_count"},
    ]
    theme_sections = []
    for t in THEMES:
        cat_objs = Category.objects.filter(name__in=t["categories"])
        s, e = t["start"], t["start"] + 4
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
                .select_related('category')[0:4]
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
