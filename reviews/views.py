from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

from restaurants.models import Restaurant
from .forms import ReviewForm
from .models import Review, ReviewReply


# 리뷰 작성
@login_required
def create_review(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)
    # ✅ 사장님 계정은 리뷰 작성 불가
    if hasattr(request.user, 'owner_profile'):
        messages.error(request, "사장님 계정은 리뷰를 작성할 수 없어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)
    # 1. 정렬 기준 가져오기 (기본값을 'rating_high'로 설정)
    sort = request.GET.get('sort', 'rating_high')
    existing_reviews = Review.objects.filter(restaurant=restaurant).select_related('reply')

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
    reviews = Review.objects.all().select_related("author", "restaurant", "reply")

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
    sort = request.GET.get('sort', 'rating_high')  # 정렬 값 읽기 (기본값: 별점 높은순)

    # 1. 사장님(OWNER)인 경우
    if hasattr(request.user, 'owner_profile'):
        # 🚨 순서 중요: 데이터부터 먼저 가져오고!
        replies = ReviewReply.objects.filter(
            author=request.user
        ).select_related("review", "review__restaurant", "review__author")

        # 그 다음에 정렬하기!
        if sort == 'latest':
            replies = replies.order_by('-created_at')
        elif sort == 'rating_low':
            replies = replies.order_by('review__rating', '-created_at')
        else: # rating_high (기본값)
            replies = replies.order_by('-review__rating', '-created_at')

        return render(request, "reviews/list.html", {
            "replies": replies,
            "is_owner": True,
            "current_sort": sort,
        })

    # 2. 일반 유저인 경우
    # 🚨 여기도 순서 중요: 데이터부터 먼저 가져오고!
    reviews = Review.objects.filter(author=request.user).select_related("restaurant", "reply")

    # 그 다음에 정렬하기!
    if sort == 'latest':
        reviews = reviews.order_by('-created_at')
    elif sort == 'rating_low':
        reviews = reviews.order_by('rating', '-created_at')
    else: # rating_high (기본값)
        reviews = reviews.order_by('-rating', '-created_at')

    return render(request, "reviews/list.html", {
        "reviews": reviews,
        "is_mypage": True,
        "current_sort": sort,
    })


# -------------------------------------------------------
# ✅ 새로 추가 - 사장님 답글 작성
# -------------------------------------------------------
@login_required
def reply_create(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    restaurant = review.restaurant

    # 권한 체크: 이 식당의 owner인지만 확인
    if restaurant.owner != request.user:
        messages.error(request, "본인 식당의 리뷰에만 답글을 달 수 있어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    # 이미 답글 있으면 차단
    if hasattr(review, 'reply'):
        messages.error(request, "이미 답글이 있어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            messages.error(request, "답글 내용을 입력해주세요.")
            return redirect("restaurants:detail", pk=restaurant.pk)

        ReviewReply.objects.create(
            review=review,
            author=request.user,
            content=content
        )
        messages.success(request, "답글이 등록됐어요! ✅")
        return redirect("restaurants:detail", pk=restaurant.pk)

    # GET 요청은 그냥 detail로 돌려보냄 (모달 방식이라 필요없음)
    return redirect("restaurants:detail", pk=restaurant.pk)


# -------------------------------------------------------
# ✅ 새로 추가 - 사장님 답글 수정
# -------------------------------------------------------
@login_required
def reply_edit(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    restaurant = review.restaurant

    # 권한 체크
    if restaurant.owner != request.user:
        messages.error(request, "본인 식당의 답글만 수정할 수 있어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    # 답글 없으면 차단
    if not hasattr(review, 'reply'):
        messages.error(request, "수정할 답글이 없어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            messages.error(request, "답글 내용을 입력해주세요.")
            return redirect("restaurants:detail", pk=restaurant.pk)

        review.reply.content = content
        review.reply.save()
        messages.success(request, "답글이 수정됐어요! ✅")
        return redirect("restaurants:detail", pk=restaurant.pk)

    # GET 요청은 그냥 detail로 돌려보냄 (모달 방식이라 필요없음)
    return redirect("restaurants:detail", pk=restaurant.pk)


# -------------------------------------------------------
# ✅ 새로 추가 - 사장님 답글 삭제
# -------------------------------------------------------
@login_required
def reply_delete(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    restaurant = review.restaurant

    # 권한 체크
    if restaurant.owner != request.user:
        messages.error(request, "본인 식당의 답글만 삭제할 수 있어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    # 답글 없으면 차단
    if not hasattr(review, 'reply'):
        messages.error(request, "삭제할 답글이 없어요.")
        return redirect("restaurants:detail", pk=restaurant.pk)

    if request.method == "POST":
        review.reply.delete()
        messages.success(request, "답글이 삭제됐어요. 🗑️")
        return redirect("restaurants:detail", pk=restaurant.pk)

    return redirect("restaurants:detail", pk=restaurant.pk)