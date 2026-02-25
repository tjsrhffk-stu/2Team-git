from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.utils.http import url_has_allowed_host_and_scheme

from restaurants.models import Restaurant
from .models import Favorite


# 1. 즐겨찾기 토글 (AJAX + 일반 요청 모두 처리)
@login_required
def toggle_favorite(request, restaurant_id):
    # 식당 존재 여부 확인
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

    # 해당 유저와 식당의 즐겨찾기 데이터 확인 (있으면 가져오고 없으면 생성)
    obj, created = Favorite.objects.get_or_create(
        user=request.user,
        restaurant=restaurant
    )

    if not created:
        # 이미 데이터가 있었다면 (다시 눌렀을 때) 삭제
        obj.delete()
        is_favorite = False
    else:
        # 새로 생성되었다면 즐겨찾기 등록
        is_favorite = True

    # AJAX 요청 처리 (프론트엔드에서 비동기로 처리할 경우)
    if (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
        or request.headers.get('Accept') == 'application/json'
    ):
        return JsonResponse({'is_favorite': is_favorite})

    # ✅ 일반 요청 처리: next 파라미터가 있으면 우선 그곳으로 복귀
    next_url = request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)

    # 기본: 식당 상세 페이지로 이동
    # (프로젝트 urls.py 설정에 맞춰 restaurant_id 인자 사용)
    return redirect("restaurants:detail", restaurant_id=restaurant_id)


# 2. 즐겨찾기 목록 페이지
@login_required
def favorite_list(request):
    # annotate를 사용하여 각 식당의 평균 별점과 리뷰 개수를 한 번의 쿼리로 가져옴 (성능 최적화)
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related('restaurant')
        .annotate(
            avg_rating=Avg('restaurant__reviews__rating'),
            review_count=Count('restaurant__reviews')
        )
        .order_by('-created_at')
    )

    # 소수점 첫째 자리 반올림 처리 (필요한 경우)
    for fav in favorites:
        if fav.avg_rating:
            fav.avg_rating = round(fav.avg_rating, 1)

    return render(request, 'favorites/list.html', {
        'favorites': favorites,
    })