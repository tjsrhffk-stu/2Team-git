"""
유저 초기화 + 리뷰 재생성 커맨드.

1. admin을 제외한 모든 유저 삭제 (리뷰 CASCADE 삭제)
2. admin이 쓴 리뷰 삭제
3. 한국인 이름 기반 30명 유저 생성
4. 식당당 랜덤 3~12개 리뷰, 별점도 낮은 것 포함해서 현실적으로 분배

사용법:
    python manage.py reset_users_reviews
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant
from reviews.models import Review

User = get_user_model()

# ── 한국 이름 풀 (30명) ────────────────────────────────────────────────────
KOREAN_USERS = [
    ("김민준", "minj_kim"),     ("이서연", "seoyeon_lee"),   ("박지호", "jiho_park"),
    ("최수아", "sua_choi"),     ("정우진", "woojin_jung"),   ("강예린", "yerin_kang"),
    ("윤도현", "dohyun_yoon"),  ("임나연", "nayeon_lim"),    ("한태양", "taeyang_han"),
    ("오지유", "jiyu_oh"),      ("서현우", "hyunwoo_seo"),   ("신아름", "areum_shin"),
    ("권민서", "minseo_kwon"),  ("조현준", "hyunjun_cho"),   ("배소희", "sohee_bae"),
    ("유승민", "seungmin_yoo"), ("송지은", "jieun_song"),    ("홍세진", "sejin_hong"),
    ("문가은", "gaeun_moon"),   ("노준혁", "junhyuk_roh"),   ("양하늘", "haneul_yang"),
    ("전다은", "daeun_jeon"),   ("고민재", "minjae_ko"),     ("남지원", "jiwon_nam"),
    ("류가람", "garam_ryu"),    ("심예지", "yeji_shim"),     ("원태현", "taehyun_won"),
    ("방소라", "sora_bang"),    ("하준서", "junseo_ha"),     ("천유나", "yuna_cheon"),
]

# ── 별점 분포 (현실적) ─────────────────────────────────────────────────────
# (별점, 가중치) — 5점이 가장 많고, 1~2점도 적당히 포함
RATING_WEIGHTS = [
    (1, 5),   # 5%
    (2, 8),   # 8%
    (3, 15),  # 15%
    (4, 35),  # 35%
    (5, 37),  # 37%
]
RATINGS      = [r for r, w in RATING_WEIGHTS]
RATING_PROBS = [w for r, w in RATING_WEIGHTS]

# ── 리뷰 템플릿: 별점별로 분리 ─────────────────────────────────────────────
# 형식: (내용, 별점)
REVIEW_TEMPLATES: dict[str, dict[int, list[str]]] = {
    "한식": {
        5: [
            "집밥 느낌이 나는 따뜻한 음식이었어요. 자주 올 것 같아요.",
            "반찬이 풍성하고 간이 딱 맞았습니다. 가성비도 좋아요.",
            "사장님이 친절하시고 음식도 맛있었어요.",
            "된장찌개가 정말 깊은 맛이 났어요. 추천합니다!",
            "삼겹살이 신선하고 잡내 없이 맛있었어요.",
            "비빔밥 최고! 고추장이 특히 맛있네요.",
        ],
        4: [
            "양이 넉넉해서 만족스러웠어요. 재방문 의사 있습니다.",
            "음식이 나오는 속도가 빠르고 맛도 좋았어요.",
            "가격 대비 훌륭한 한 끼였습니다.",
            "전반적으로 맛있었는데 국물이 조금 짰어요.",
            "분위기 좋고 음식도 괜찮았어요.",
        ],
        3: [
            "맛은 괜찮은데 가격이 조금 비싼 것 같아요.",
            "주차가 너무 불편해서 별점 깎았어요. 음식은 무난했습니다.",
            "기대를 너무 많이 했나봐요. 평범한 수준이었어요.",
            "음식은 보통인데 서비스가 좀 불친절했어요.",
        ],
        2: [
            "음식이 너무 짰어요. 한 끼 먹기도 힘들었습니다.",
            "기다림이 너무 길었고 음식도 별로였어요.",
            "위생 상태가 조금 걱정됐어요. 다시 오기는 힘들 것 같아요.",
        ],
        1: [
            "음식에서 이물질이 나왔어요. 정말 실망스러웠습니다.",
            "서비스도 최악이고 음식도 맛없었어요. 재방문 절대 안 합니다.",
        ],
    },
    "일식": {
        5: [
            "초밥이 신선하고 밥의 간이 딱 맞아요.",
            "라멘 국물이 진하고 깊은 맛이 났어요.",
            "일본 현지 느낌이 나는 정통 맛이에요.",
            "신선한 재료를 사용하는 게 느껴졌어요.",
            "서비스가 세심하고 음식 수준도 높아요.",
        ],
        4: [
            "점심 특선 세트가 가성비 최고입니다!",
            "돈카츠가 바삭하고 육즙이 풍부해요.",
            "웨이팅이 있지만 그만한 가치가 있어요.",
            "전반적으로 만족스러웠어요. 다음에 또 올게요.",
        ],
        3: [
            "맛은 있는데 양이 조금 적어요.",
            "가격 대비 평범한 수준이에요.",
            "분위기는 좋은데 음식이 기대 이하였어요.",
        ],
        2: [
            "신선도가 조금 걱정됐어요. 초밥이 퍽퍽했습니다.",
            "가격이 너무 비싸요. 이 가격이면 다른 곳 가겠어요.",
        ],
        1: [
            "생선이 신선하지 않은 것 같았어요. 먹고 나서 배가 아팠습니다.",
        ],
    },
    "중식": {
        5: [
            "짜장면 소스가 진하고 면발이 탱탱해요.",
            "탕수육 바삭함이 오래 유지됐어요. 최고!",
            "짬뽕 국물이 칼칼하고 해물이 풍부했어요.",
            "딤섬이 정말 맛있었어요. 피가 얇고 속이 가득!",
        ],
        4: [
            "양이 많아서 두 명이 나눠 먹기 좋아요.",
            "배달도 빠르고 음식도 식지 않게 왔어요.",
            "점심 세트 가성비 최고입니다.",
            "마라탕 향이 진짜 마라 맛이 났어요.",
        ],
        3: [
            "짜장면은 맛있는데 다른 메뉴는 평범했어요.",
            "기름기가 조금 많아서 느끼했어요.",
            "서비스가 느려서 좀 불편했어요.",
        ],
        2: [
            "짬뽕이 너무 짜고 해물이 신선하지 않았어요.",
            "탕수육이 눅눅하게 나왔어요. 실망스러웠습니다.",
        ],
        1: [
            "주문한 것과 다른 음식이 나왔는데 교환도 안 해줬어요.",
        ],
    },
    "양식": {
        5: [
            "파스타 면이 알단테로 완벽하게 익었어요.",
            "스테이크 굽기가 정확해서 만족스러웠어요.",
            "분위기가 로맨틱해서 데이트 장소로 최고예요.",
            "리조또가 크리미하고 재료가 신선했어요.",
            "서비스가 프로페셔널해서 기분 좋게 식사했어요.",
        ],
        4: [
            "피자 도우가 얇고 바삭해서 좋아요.",
            "빵이 직접 구운 거라 향이 정말 좋아요.",
            "디저트까지 완벽한 코스였습니다.",
            "전반적으로 만족스러운 식사였어요.",
        ],
        3: [
            "가격이 조금 높은 편이에요. 맛은 괜찮았어요.",
            "파스타 간이 싱거웠어요. 소금을 더 달라고 해야 했어요.",
            "분위기는 좋은데 음식이 기대 이하였어요.",
        ],
        2: [
            "스테이크를 미디움으로 주문했는데 너무 웰던으로 나왔어요.",
            "파스타가 퍼져서 나왔어요. 조리 관리가 아쉬웠습니다.",
        ],
        1: [
            "음식이 너무 짜고 서비스도 불친절했어요. 다시는 안 갑니다.",
        ],
    },
    "카페": {
        5: [
            "커피 향이 진하고 산미 조절이 잘 됐어요.",
            "인테리어가 감각적이고 사진 찍기 좋아요.",
            "바리스타가 커피에 대한 열정이 느껴졌어요.",
            "케이크가 촉촉하고 달지 않아서 좋아요.",
            "시즌 한정 음료가 정말 맛있었어요!",
        ],
        4: [
            "노트북 작업하기 좋은 아늑한 분위기예요.",
            "창가 자리에서 보이는 뷰가 멋있어요.",
            "디저트와 음료 페어링이 잘 됐어요.",
            "차 종류가 다양해서 선택지가 많아 좋아요.",
        ],
        3: [
            "커피 맛은 괜찮은데 가격이 조금 비싸요.",
            "분위기는 좋은데 소음이 좀 있어요.",
            "자리가 불편해서 오래 앉아있기 힘들었어요.",
        ],
        2: [
            "커피가 너무 쓰고 음료 온도가 너무 뜨거웠어요.",
            "케이크가 마른 게 진열된 것 같았어요. 신선하지 않았어요.",
        ],
        1: [
            "주문 실수를 했는데 교환이나 환불을 거부했어요. 황당했습니다.",
        ],
    },
    "패스트푸드": {
        5: [
            "버거 패티가 두툼하고 육즙이 살아있어요.",
            "치킨이 겉은 바삭 속은 촉촉해요.",
            "가격 대비 양이 많아서 만족스러워요.",
        ],
        4: [
            "감자튀김이 바삭하고 따뜻하게 나왔어요.",
            "주문 후 빠르게 나와서 바쁠 때 딱이에요.",
            "세트 메뉴 구성이 합리적이에요.",
            "소스 종류가 다양해서 골라 먹는 재미가 있어요.",
        ],
        3: [
            "맛은 보통이에요. 특별한 건 없었지만 무난했어요.",
            "버거가 식어서 나왔어요. 좀 아쉬웠습니다.",
        ],
        2: [
            "주문이 잘못 들어왔는데 수정도 오래 걸렸어요.",
            "감자튀김이 눅눅하고 음료가 너무 달았어요.",
        ],
        1: [
            "머리카락이 나왔어요. 환불도 제대로 안 해줬습니다.",
        ],
    },
    "기타": {
        5: [
            "분위기도 좋고 음식도 맛있었어요.",
            "주변 맛집 중에서 손에 꼽는 곳이에요.",
            "처음 방문했는데 단골 될 것 같아요.",
            "재료가 신선하고 조리가 잘 됐어요.",
        ],
        4: [
            "서비스가 친절하고 음식이 금방 나왔어요.",
            "특별한 날 방문하기 좋은 분위기예요.",
            "음식 퀄리티가 기대 이상이었어요.",
        ],
        3: [
            "맛은 그저 그랬어요. 기대보다 아쉬웠습니다.",
            "가격이 좀 비싸요. 보통 수준의 음식이에요.",
        ],
        2: [
            "음식 간이 맞지 않았어요. 실망스러웠습니다.",
            "웨이팅이 너무 길었고 결과도 별로였어요.",
        ],
        1: [
            "전혀 추천하지 않아요. 서비스도 음식도 최악이었어요.",
        ],
    },
}


def pick_rating() -> int:
    """현실적인 별점 분포로 랜덤 선택"""
    return random.choices(RATINGS, weights=RATING_PROBS, k=1)[0]


def pick_review_count() -> int:
    """식당당 리뷰 수 — 3~12개, 대부분 3~6개"""
    # 가중치: 3개 30%, 4~5개 35%, 6~8개 20%, 9~12개 15%
    return random.choices(
        [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        weights=[14, 11, 10, 9, 7, 6, 5, 5, 4, 4],
        k=1
    )[0]


class Command(BaseCommand):
    help = "admin 제외 유저 삭제 후 30명 생성, 리뷰 재생성 (별점 현실적 분포)"

    def handle(self, *args, **options):

        # ── Step 1: non-admin 유저 삭제 (CASCADE → 리뷰 자동 삭제) ──────
        self.stdout.write("1. 기존 유저(admin 제외) 및 연관 리뷰 삭제 중...")
        deleted, detail = User.objects.exclude(is_superuser=True).delete()
        self.stdout.write(f"   삭제: {detail}")

        # ── Step 2: admin 리뷰 삭제 ──────────────────────────────────────
        self.stdout.write("2. admin 리뷰 삭제 중...")
        admin_del, _ = Review.objects.filter(author__is_superuser=True).delete()
        self.stdout.write(f"   admin 리뷰 {admin_del}개 삭제 / 남은 리뷰: {Review.objects.count()}개")

        # ── Step 3: 30명 유저 생성 ──────────────────────────────────────
        self.stdout.write("3. 한국인 유저 30명 생성 중...")
        created_users = []
        for full_name, username in KOREAN_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": full_name,
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                }
            )
            if created:
                user.set_password("testpass123!")
                user.save()
            created_users.append(user)
        self.stdout.write(self.style.SUCCESS(f"   유저 {len(created_users)}명 생성 완료"))

        # ── Step 4: 리뷰 재생성 ──────────────────────────────────────────
        self.stdout.write("4. 리뷰 재생성 중 (식당당 3~12개, 별점 현실적 분포)...")
        restaurants = Restaurant.objects.select_related("category").all()
        total = restaurants.count()
        review_count = 0
        bulk_list = []

        for seq, restaurant in enumerate(restaurants.iterator(), 1):
            cat_name = restaurant.category.name if restaurant.category else "기타"
            cat_templates = REVIEW_TEMPLATES.get(cat_name, REVIEW_TEMPLATES["기타"])

            n = pick_review_count()
            # 이 식당에 작성할 유저들 (중복 없이 랜덤 선택)
            authors = random.sample(created_users, min(n, len(created_users)))

            for author in authors:
                rating = pick_rating()
                pool = cat_templates.get(rating) or cat_templates.get(4, [])
                if not pool:
                    pool = ["방문했어요."]
                content = random.choice(pool)
                bulk_list.append(Review(
                    restaurant=restaurant,
                    author=author,
                    rating=rating,
                    content=content,
                ))
                review_count += 1

            # 1000개씩 bulk_create
            if len(bulk_list) >= 1000:
                Review.objects.bulk_create(bulk_list)
                bulk_list = []

            if seq % 300 == 0:
                self.stdout.write(f"   {seq}/{total} 식당 처리 중 (리뷰 {review_count}개)...")

        # 나머지 저장
        if bulk_list:
            Review.objects.bulk_create(bulk_list)

        self.stdout.write(self.style.SUCCESS(
            f"\n완료!\n"
            f"  유저: {len(created_users)}명\n"
            f"  리뷰: {review_count}개 (평균 {review_count/total:.1f}개/식당)\n"
            f"  비밀번호: testpass123! (전체 공통)"
        ))

        # 별점 분포 출력
        from django.db.models import Count
        self.stdout.write("\n별점 분포:")
        dist = (
            Review.objects.values("rating")
            .annotate(cnt=Count("id"))
            .order_by("rating")
        )
        total_r = Review.objects.count()
        for d in dist:
            bar = "█" * (d["cnt"] * 20 // total_r)
            self.stdout.write(f"  {d['rating']}점: {d['cnt']:5d}개 ({d['cnt']*100/total_r:.1f}%) {bar}")
