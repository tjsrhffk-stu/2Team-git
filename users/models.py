from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
# ✅ 예약(Reservation) 모델 등록 (models.py 밖에 분리해둔 파일을 Django가 인식하도록 import)
from .reservation_models import Reservation  # noqa: E402,F401

class Profile(models.Model):
    """공통 프로필(모든 사용자 공통)
    - 이메일 인증/비밀번호 재설정 같은 토큰류를 보관
    - ✅ user_type(일반/사업자) 같은 '역할' 정보도 여기서 관리 (기본 User 모델 확장 불가 이슈 해결)
    """

    class UserType(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        OWNER = "OWNER", "Owner"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # ✅ 일반/사업자 구분 (나중에 이중화/운영 시에도 '명시적' 기준이 되도록)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.CUSTOMER,
        db_index=True,
    )

    email_token = models.CharField(max_length=64, null=True, blank=True)
    email_token_created_at = models.DateTimeField(null=True, blank=True)

    reset_token = models.CharField(max_length=64, null=True, blank=True)
    reset_token_created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile<{self.user.username}> ({self.user_type})"


class CustomerProfile(models.Model):
    """✅ 일반회원 전용 테이블
    - Admin에서 'Customers'처럼 별도 메뉴로 관리하기 위한 분리 테이블
    - 일반회원 전용 필드가 생기면 여기에 추가
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"Customer<{self.user.username}>"


class OwnerProfile(models.Model):
    """✅ 사업자(사장) 전용 테이블"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="owner_profile")

    # ✅ 기존 DB에 OwnerProfile이 있어도 마이그레이션 막히지 않게 null 허용
    # ✅ 가입 로직에서 business_number 입력을 '필수'로 강제함
    business_number = models.CharField(max_length=10, unique=True, null=True, blank=True)

    class Meta:
        verbose_name = "Owner"
        verbose_name_plural = "Owners"

    def __str__(self):
        return f"Owner<{self.user.username}> ({self.business_number})"


# -------------------------------------------------------
# ✅ Admin에서 'Users'를 두 메뉴로 분리하기 위한 Proxy Model
#   - DB 테이블은 User 그대로
#   - 목록/검색/필터만 따로 보이게 분리
# -------------------------------------------------------
class CustomerUser(User):
    class Meta:
        proxy = True
        verbose_name = "Customer User"
        verbose_name_plural = "Customer Users"


class OwnerUser(User):
    class Meta:
        proxy = True
        verbose_name = "Owner User"
        verbose_name_plural = "Owner Users"


@receiver(post_save, sender=User)
def create_profiles(sender, instance, created, **kwargs):
    """✅ 신규 유저 생성 시 공통 Profile은 항상 보장.
    - 기본 user_type은 CUSTOMER
    - CustomerProfile도 기본 생성(관리 편의)
      * 단, 사업자 가입 로직에서는 user_type을 OWNER로 바꾸고 OwnerProfile을 만들며,
        필요하면 CustomerProfile을 제거함.
    """
    if created:
        Profile.objects.create(user=instance)
        CustomerProfile.objects.get_or_create(user=instance)