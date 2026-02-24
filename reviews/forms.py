from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        # "photo" -> "image"로 변경
        fields = ["rating", "content", "image"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "content": forms.Textarea(attrs={"rows": 4}),
        }