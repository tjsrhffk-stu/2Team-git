from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from restaurants.models import Restaurant
from .forms import ReviewForm
from .models import Review


# 리뷰 작성
@login_required
def create_review(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

    # 1. 정렬 기준 가져오기 (기본값을 'rating_high'로 설정)
    sort = request.GET.get('sort', 'rating_high')
    existing_reviews = Review.objects.filter(restaurant=restaurant)

    # 2. 정렬 로직
    if sort == 'latest':
        existing_reviews = existing_reviews.order_by('-created_at')
    elif sort == 'rating_low':
        existing_reviews = existing_reviews.order_by('rating', '-created_at')
    else:  # rating_high (기본값)
        existing_reviews = existing_reviews.order_by('-rating', '-created_at')

    # ✅ next 처리: (마이페이지 등) 원래 페이지로 돌아가기 위한 값
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.restaurant = restaurant
            review.author = request.user
            review.save()
            messages.success(request, "리뷰가 작성되었어요! ✅")

            # ✅ next 우선 복귀
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            return redirect("restaurants:detail", pk=restaurant.id)
    else:
        form = ReviewForm()

    return render(request, "reviews/create.html", {
        "form": form,
        "restaurant": restaurant,
        "existing_reviews": existing_reviews,  # HTML로 전달
        "current_sort": sort,                  # 현재 어떤 정렬인지 HTML이 알게 함
        "next": next_url,                      # 템플릿에서 hidden으로 넘기고 싶으면 사용
    })


# 리뷰 수정
@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.author != request.user:
        messages.error(request, "본인이 작성한 리뷰만 수정할 수 있어요.")
        return redirect("restaurants:detail", pk=review.restaurant.id)

    # ✅ next 처리
    next_url = request.GET.get("next")

    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "리뷰가 수정되었어요! ✅")

            # ✅ next 우선 복귀
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            return redirect("restaurants:detail", pk=review.restaurant.id)
    else:
        form = ReviewForm(instance=review)

    return render(request, "reviews/create.html", {
        "form": form,
        "restaurant": review.restaurant,
        "edit_mode": True,
        "review": review,
        "next": next_url,
    })


# 리뷰 삭제
@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.author != request.user:
        messages.error(request, "본인이 작성한 리뷰만 삭제할 수 있어요.")
        return redirect("restaurants:detail", pk=review.restaurant.id)

    restaurant_id = review.restaurant.id

    # ✅ next 처리
    next_url = request.GET.get("next")

    if request.method == "POST":
        review.delete()
        messages.success(request, "리뷰가 삭제되었어요. 🗑️")

        # ✅ next 우선 복귀
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)

    return redirect("restaurants:detail", pk=restaurant_id)


# 리뷰 전체 목록
def review_list(request):
    sort = request.GET.get('sort', 'latest')
    reviews = Review.objects.all().select_related("author", "restaurant")

    if sort == 'rating_high':
        reviews = reviews.order_by('-rating', '-id')
    elif sort == 'rating_low':
        reviews = reviews.order_by('rating', '-id')
    else:
        reviews = reviews.order_by('-id')

    return render(request, "reviews/list.html", {"reviews": reviews})


# ✅ 4. 내가 쓴 리뷰 목록 (새로 추가됨)
@login_required
def my_reviews(request):
    """
    현재 로그인한 유저가 작성한 리뷰만 필터링하여 
    마이페이지 내 리뷰 목록으로 보여줍니다.
    """
    reviews = Review.objects.filter(author=request.user).select_related("restaurant").order_by('-created_at')
    return render(request, "reviews/list.html", {
        "reviews": reviews,
        "is_mypage": True  # 템플릿에서 마이페이지 전용 UI를 보여주고 싶을 때 사용
    })