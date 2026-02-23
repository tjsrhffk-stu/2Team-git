from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model  = Review
        fields = ["rating", "content", "photo"]
        widgets = {
            "rating": forms.Select(
                choices=[(i, f"{'★' * i} ({i}점)") for i in range(1, 6)],
            ),
            "content": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "솔직한 리뷰를 남겨주세요!",
            }),
        }
        labels = {
            "rating": "별점",
            "content": "리뷰 내용",
            "photo":   "사진 (선택)",
        }