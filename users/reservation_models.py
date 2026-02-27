from django.db import models
from django.conf import settings

from restaurants.models import Restaurant


class Reservation(models.Model):
    """예약 테이블 (일반회원/사장 공통 조회용)

    - 예약 생성/수정/취소: 일반회원(CUSTOMER)
    - 예약 조회/취소: 사장(OWNER) (본인 식당 예약만)
    """

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"   # 신청
        CONFIRMED = "CONFIRMED", "Confirmed"   # 확정(확장은 나중에)
        CANCELED = "CANCELED", "Canceled"      # 취소(회원/사장)
        REJECTED = "REJECTED", "Rejected"      # 거절(확장은 나중에)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="reservations",
    )

    reserved_at = models.DateTimeField()
    party_size = models.PositiveSmallIntegerField(default=1)
    request_note = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Reservation<{self.id}> {self.user} -> {self.restaurant} @ {self.reserved_at}"

    @property
    def is_active(self):
        return self.status not in {self.Status.CANCELED, self.Status.REJECTED}