"""
MealDB API로 카테고리별 실제 음식 이미지를 다운로드하고
리뷰를 추가하는 관리 커맨드.

사용법:
    python manage.py seed_images_reviews
    python manage.py seed_images_reviews --images-only
    python manage.py seed_images_reviews --reviews-only
    python manage.py seed_images_reviews --reviews-per 3
"""

import random
import time

import requests
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from restaurants.models import Restaurant, Category
from reviews.models import Review

User = get_user_model()

# MealDB 카테고리/지역 → 우리 카테고리 매핑
MEALDB_AREAS = {
    "한식":    ["Korean"],
    "일식":    ["Japanese"],
    "중식":    ["Chinese"],
    "양식":    ["French", "Italian", "American"],
    "카페":    [],          # 카테고리 Dessert 사용
    "패스트푸드": ["American"],
    "기타":    ["Indian", "Mexican", "Thai", "Greek"],
}

REVIEW_TEMPLATES = {
    "한식": [
        ("맛있어요! 고기가 정말 신선하고 양도 푸짐했어요. 다음에도 꼭 올게요.", 5),
        ("김치찌개가 집밥 느낌 그대로예요. 가격도 합리적이고 자주 오고 싶은 곳.", 4),
        ("반찬이 정말 다양하게 나와서 좋았어요. 직원분들도 친절하셨습니다.", 5),
        ("삼겹살이 두툼하게 잘려 나오고 굽기도 완벽했어요. 강추!", 5),
        ("점심 특선 가성비 최고입니다. 된장찌개 하나만으로도 배가 든든해요.", 4),
        ("비빔밥 맛집이에요. 야채가 신선하고 고추장 소스가 일품!", 5),
        ("냉면 맛이 진하고 시원해요. 여름엔 여기서 해결합니다.", 4),
        ("갈비찜 간이 딱 맞아요. 고기도 부드럽고 반찬도 깔끔합니다.", 4),
        ("해장국 먹으러 왔다가 단골이 됐어요. 국물이 진하고 얼큰해요.", 5),
        ("제육볶음 매콤달콤해서 밥 두 공기 뚝딱했어요.", 5),
    ],
    "일식": [
        ("초밥이 신선하고 밥 간이 완벽해요. 진짜 일본 맛입니다!", 5),
        ("라멘 국물이 진하고 면이 탱탱해요. 계란 반숙도 딱 맞게 익혀줬어요.", 5),
        ("돈카츠 바삭함이 장난 아니에요. 소스도 직접 만드는 것 같고 맛있어요.", 4),
        ("우동 국물이 깔끔하고 면발이 쫄깃해요.", 4),
        ("오마카세 코스인데 가성비 넘쳐요. 셰프님이 친절하게 설명해주십니다.", 5),
        ("텐동 튀김이 바삭바삭하고 간장 소스가 맛있어요.", 4),
        ("사시미 플레이팅이 예쁘고 신선해요. 생선 종류도 다양합니다.", 5),
        ("야키토리 닭꼬치가 숯불 향이 나서 더 맛있어요.", 4),
    ],
    "중식": [
        ("짜장면이 면발부터 소스까지 정통 중국 느낌이에요.", 5),
        ("탕수육 바삭함이 유지되고 소스가 새콤달콤해요.", 5),
        ("마라탕 국물이 칼칼하고 재료가 신선해요. 양도 많아요.", 4),
        ("딤섬이 쫄깃하고 속 재료가 알차요.", 5),
        ("짬뽕 국물이 시원하고 해산물이 가득해요.", 4),
        ("마파두부 매운맛이 강렬해요. 밥 도둑 그 자체입니다!", 4),
        ("양꼬치가 촉촉하고 향신료 향이 적당해요.", 5),
    ],
    "양식": [
        ("파스타 면 삶기가 알덴테로 딱 맞아요. 크림 소스가 진하고 고소합니다.", 5),
        ("스테이크가 요청한 굽기 그대로 나왔어요. 미디엄 레어가 완벽했습니다.", 5),
        ("피자 도우가 얇고 바삭해요. 토핑이 넘치게 올라와요.", 4),
        ("리조또 쌀이 살살 녹는 느낌이에요. 해산물도 신선합니다.", 4),
        ("브런치 세트가 예쁘게 나와요. 인스타 감성이면서 맛도 좋습니다.", 5),
        ("연어 스테이크가 촉촉하고 레몬 버터 소스가 일품이에요.", 4),
        ("뇨키가 부드럽고 트러플 향이 은은하게 나요.", 5),
    ],
    "카페": [
        ("라테 아트가 예쁘고 커피 맛도 진해요. 원두 향이 오래 남아요.", 5),
        ("브런치 메뉴가 다양하고 맛있어요. 에그베네딕트가 특히 추천!", 5),
        ("조용하고 분위기 좋아서 작업하기 최적이에요. 콘센트도 많아요.", 4),
        ("디저트 케이크가 너무 예쁘고 맛있어요.", 5),
        ("아이스 아메리카노 농도가 딱 맞아요. 원두 선택도 가능합니다.", 4),
        ("크루아상이 겹겹이 바삭해요. 커피랑 세트로 시키면 완벽합니다.", 5),
        ("말차 라테가 진하고 달지 않아서 딱 제 취향이에요.", 4),
        ("테라스 자리가 있어서 날씨 좋을 때 오기 딱 좋아요.", 5),
    ],
    "패스트푸드": [
        ("버거 패티가 육즙이 넘쳐요. 수제버거 수준!", 5),
        ("치킨이 바삭바삭하고 양념이 잘 배어 있어요.", 4),
        ("감자튀김이 얇고 바삭해요. 양도 많아요.", 4),
        ("세트 메뉴 가성비 좋아요. 음료까지 포함해서 대만족!", 5),
        ("포장해도 바삭함이 유지돼요. 기름기도 적고 깔끔합니다.", 4),
    ],
    "기타": [
        ("예상보다 맛있어서 깜짝 놀랐어요. 다음에 또 오고 싶어요.", 4),
        ("가격 대비 퀄리티가 정말 좋아요. 서비스도 친절해요.", 5),
        ("처음 와봤는데 단골이 될 것 같아요.", 5),
        ("분위기가 좋고 음식도 맛있어요. 데이트 장소로 강력 추천!", 4),
        ("재료가 신선하고 조리법이 독특해요.", 5),
        ("직원분들이 정말 친절하고 음식도 빨리 나와요.", 4),
    ],
}


def fetch_meal_images(areas: list[str]) -> list[str]:
    """MealDB API에서 해당 지역 음식 이미지 URL 목록 반환"""
    urls = []
    for area in areas:
        try:
            resp = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/filter.php?a={area}",
                timeout=10,
            )
            meals = resp.json().get("meals") or []
            urls += [m["strMealThumb"] for m in meals if m.get("strMealThumb")]
        except Exception as e:
            print(f"  MealDB 오류 ({area}): {e}")
    return urls


def fetch_dessert_images() -> list[str]:
    """MealDB 디저트 카테고리 이미지 (카페용)"""
    try:
        resp = requests.get(
            "https://www.themealdb.com/api/json/v1/1/filter.php?c=Dessert",
            timeout=10,
        )
        meals = resp.json().get("meals") or []
        return [m["strMealThumb"] for m in meals if m.get("strMealThumb")]
    except Exception as e:
        print(f"  MealDB 디저트 오류: {e}")
        return []


def download_image(url: str, timeout: int = 15) -> bytes | None:
    """이미지 URL에서 바이트 다운로드"""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
            return resp.content
    except Exception as e:
        print(f"  다운로드 실패 ({url[:60]}): {e}")
    return None


class Command(BaseCommand):
    help = "MealDB 음식 이미지와 리뷰를 음식점에 추가합니다."

    def add_arguments(self, parser):
        parser.add_argument("--images-only",  action="store_true")
        parser.add_argument("--reviews-only", action="store_true")
        parser.add_argument("--reviews-per",  type=int, default=3,
                            help="음식점당 리뷰 수 (기본 3)")

    def handle(self, *args, **options):
        do_images  = not options["reviews_only"]
        do_reviews = not options["images_only"]
        reviews_per = min(max(options["reviews_per"], 1), 5)

        users = list(User.objects.filter(is_active=True, is_superuser=False))
        if not users:
            self.stderr.write("활성 사용자 없음 → 리뷰 생성 불가")
            do_reviews = False

        # ── 1. 이미지 다운로드 & 할당 ─────────────────────────────────
        if do_images:
            self.stdout.write("\n🖼️  MealDB에서 이미지 URL 수집 중...")

            img_pool: dict[str, list[str]] = {}

            for cat_name, areas in MEALDB_AREAS.items():
                if cat_name == "카페":
                    urls = fetch_dessert_images()
                else:
                    urls = fetch_meal_images(areas)

                random.shuffle(urls)
                img_pool[cat_name] = urls
                self.stdout.write(f"  [{cat_name}] {len(urls)}개 URL 확보")
                time.sleep(0.3)

            # 이미지 없는 카테고리는 기타 풀로 채움
            fallback = img_pool.get("기타", [])

            self.stdout.write("\n📎 음식점에 이미지 할당 중 (다운로드 포함)...")
            assigned = 0
            restaurants = (
                Restaurant.objects
                .filter(thumbnail="")
                .select_related("category")
            )
            total = restaurants.count()

            # 카테고리별 URL 인덱스 추적
            cat_idx: dict[str, int] = {k: 0 for k in img_pool}

            for seq, restaurant in enumerate(restaurants.iterator(), 1):
                cat_name = restaurant.category.name if restaurant.category else "기타"
                pool = img_pool.get(cat_name) or fallback
                if not pool:
                    continue

                idx = cat_idx.get(cat_name, 0)
                url = pool[idx % len(pool)]
                cat_idx[cat_name] = idx + 1

                img_data = download_image(url)
                if not img_data:
                    time.sleep(0.2)
                    continue

                filename = f"meal_{restaurant.pk}.jpg"
                try:
                    restaurant.thumbnail.save(filename, ContentFile(img_data), save=True)
                    assigned += 1
                except Exception as e:
                    self.stderr.write(f"  저장 실패 ({restaurant.name}): {e}")

                # 진행 상황
                if seq % 50 == 0:
                    self.stdout.write(f"  {seq}/{total} 처리 중... (성공 {assigned}개)")

                time.sleep(0.1)   # 서버 부담 줄이기

            self.stdout.write(self.style.SUCCESS(f"  ✅ 이미지 {assigned}/{total}개 완료"))

        # ── 2. 리뷰 생성 ──────────────────────────────────────────────
        if do_reviews:
            self.stdout.write("\n💬 리뷰 생성 중...")
            created = 0
            restaurants = (
                Restaurant.objects
                .filter(reviews__isnull=True)
                .select_related("category")
                .distinct()
            )
            total = restaurants.count()

            for seq, restaurant in enumerate(restaurants.iterator(), 1):
                cat_name = restaurant.category.name if restaurant.category else "기타"
                templates = REVIEW_TEMPLATES.get(cat_name, REVIEW_TEMPLATES["기타"])
                chosen = random.sample(templates, min(reviews_per, len(templates)))
                for content, rating in chosen:
                    try:
                        Review.objects.create(
                            restaurant=restaurant,
                            author=random.choice(users),
                            rating=rating,
                            content=content,
                        )
                        created += 1
                    except Exception as e:
                        self.stderr.write(f"  리뷰 실패 ({restaurant.name}): {e}")

                if seq % 300 == 0:
                    self.stdout.write(f"  {seq}/{total} 처리 중...")

            self.stdout.write(self.style.SUCCESS(f"  ✅ 리뷰 {created}개 생성 완료"))

        self.stdout.write(self.style.SUCCESS("\n🎉 모든 작업 완료!"))
