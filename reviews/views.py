from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
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

    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.restaurant = restaurant
            review.author = request.user
            review.save()
            return redirect("restaurants:detail", pk=restaurant.id)
    else:
        form = ReviewForm()

    return render(request, "reviews/create.html", {
        "form": form,
        "restaurant": restaurant,
        "existing_reviews": existing_reviews, # HTML로 전달
        "current_sort": sort  # 현재 어떤 정렬인지 HTML이 알게 함
    })


# 리뷰 수정
@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.author != request.user:
        messages.error(request, "본인이 작성한 리뷰만 수정할 수 있어요.")
        return redirect("restaurants:detail", pk=review.restaurant.id)

    if request.method == "POST":
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "리뷰가 수정되었어요! ✅")
            return redirect("restaurants:detail", pk=review.restaurant.id)
    else:
        form = ReviewForm(instance=review)

    return render(request, "reviews/create.html", {
        "form": form,
        "restaurant": review.restaurant,
        "edit_mode": True,
        "review": review,
    })


# 리뷰 삭제
@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.author != request.user:
        messages.error(request, "본인이 작성한 리뷰만 삭제할 수 있어요.")
        return redirect("restaurants:detail", pk=review.restaurant.id)

    restaurant_id = review.restaurant.id

    if request.method == "POST":
        review.delete()
        messages.success(request, "리뷰가 삭제되었어요.")

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