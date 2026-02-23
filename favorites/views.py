from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from restaurants.models import Restaurant
from .models import Favorite


# 즐겨찾기 토글 (AJAX + 일반 요청 둘 다 처리)
@login_required
def toggle_favorite(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
    obj, created = Favorite.objects.get_or_create(
        user=request.user, restaurant=restaurant
    )
    if not created:
        obj.delete()
        is_favorite = False
    else:
        is_favorite = True

    # AJAX 요청이면 JSON 반환, 일반 요청이면 상세페이지로 이동
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.content_type == 'application/json' or \
       request.headers.get('Accept') == 'application/json':
        return JsonResponse({'is_favorite': is_favorite})

    return redirect("restaurants:detail", pk=restaurant_id)


# 즐겨찾기 목록
@login_required
def favorite_list(request):
    from django.db.models import Avg, Count

    favorites = Favorite.objects.filter(
        user=request.user
    ).select_related('restaurant').prefetch_related(
        'restaurant__reviews'
    ).order_by('-created_at')

    # 각 음식점에 avg_rating, review_count 추가
    for fav in favorites:
        fav.restaurant.avg_rating = fav.restaurant.reviews.aggregate(
            avg=Avg('rating')
        )['avg']
        if fav.restaurant.avg_rating:
            fav.restaurant.avg_rating = round(fav.restaurant.avg_rating, 1)
        fav.restaurant.review_count = fav.restaurant.reviews.count()

    return render(request, 'favorites/list.html', {
        'favorites': favorites,
    })