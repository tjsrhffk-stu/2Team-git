"""
메뉴 아이템별 정확한 이미지를 저장하는 커맨드.
- 음료: TheCocktailDB API (MealDB와 같은 제작사, 무료)
- 조리 음식 / 사이드: MealDB API

사용법:
    python manage.py seed_menu_images --reset
"""

import time
import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from restaurants.models import MenuItem

# Wikipedia Commons는 User-Agent 없이 hotlinking 차단 → 사용 안 함
DIRECT_URLS: dict[str, str] = {}

# ────────────────────────────────────────────────────────────────────────────
# 2. 음료 → TheCocktailDB 검색어
#    https://www.thecocktaildb.com/api/json/v1/1/search.php?s=<query>
# ────────────────────────────────────────────────────────────────────────────
COCKTAILDB_SEARCH: dict[str, str] = {
    "소주":          "sake",              # 동아시아 전통주 이미지
    "맥주":          "beer",
    "아사히 생맥주":  "beer",
    "칭다오":         "beer",
    "하이볼":         "highball",
    "와인 (글라스)":  "wine",
    "콜라":           "rum and cola",      # Cuba Libre 이미지 사용
    "탄산수":         "club soda",
    "쉐이크":         "milkshake",
    "주스":           "orange juice",
    "에이드":         "lemonade",
    "생수":           "water",
    "아메리카노":     "espresso martini",  # 커피 계열 이미지
    "카페 라테":      "coffee",
    "카푸치노":       "b52",               # 커피 리큐어 칵테일
    "바닐라 라테":    "vanilla",
    "말차 라테":      "green tea",
}

# ────────────────────────────────────────────────────────────────────────────
# 3. 조리 음식 / 사이드 → MealDB API 검색어
# ────────────────────────────────────────────────────────────────────────────
MEALDB_SEARCH: dict[str, str] = {
    # 한식
    "김치":         "Kimchi",
    "삼겹살":       "Samgyeopsal",
    "된장찌개":     "Miso Soup",
    "김치찌개":     "Kimchi",
    "비빔밥":       "Bibimbap",
    "불고기":       "Beef Bulgogi",
    "갈비탕":       "Beef Stew",
    "냉면":         "Noodles",
    "제육볶음":     "Spicy Pork",
    "된장국":       "Miso",
    "미소시루":     "Miso Soup",
    # 일식
    "연어 초밥":    "Salmon",
    "참치 초밥":    "Tuna",
    "모듬 초밥":    "Sushi",
    "쇼유 라멘":    "Ramen",
    "돈코츠 라멘":  "Ramen",
    "돈카츠":       "Tonkatsu",
    "가라아게":     "Fried Chicken",
    "규동":         "Beef Bowl",
    "차슈":         "Pork",
    # 중식
    "짜장면":       "Noodles",
    "짬뽕":         "Seafood Noodle",
    "탕수육":       "Sweet and Sour Pork",
    "마파두부":     "Mapo Tofu",
    "북경오리":     "Duck",
    "볶음밥":       "Fried Rice",
    "딤섬":         "Dumplings",
    "짜사이":       "Pickle",
    # 양식
    "카르보나라":   "Carbonara",
    "알리오올리오": "Pasta",
    "토마토 파스타":"Tomato Pasta",
    "티본 스테이크":"Beef Steak",
    "안심 스테이크":"Beef",
    "마르게리타 피자":"Margherita Pizza",
    "리조또":       "Risotto",
    "시저 샐러드":  "Caesar Salad",
    "수프":         "Soup",
    "양장피":       "Seafood Salad",
    # 카페 / 디저트
    "크루아상":     "Croissant",
    "티라미수":     "Tiramisu",
    "치즈케이크":   "Cheesecake",
    "브런치 세트":  "Eggs Benedict",
    # 패스트푸드
    "클래식 버거":  "Burger",
    "더블 치즈버거":"Cheeseburger",
    "치킨 버거":    "Chicken Burger",
    "후라이드 치킨":"Fried Chicken",
    "콤보 세트":    "Burger",
    # 사이드
    "공기밥":       "Rice",
    "감자튀김":     "French Fries",
    "어니언링":     "Onion Rings",
    "가릭 브레드":  "Garlic Bread",
    # 기타
    "오늘의 메인":  "Roast",
    "모둠 안주":    "Antipasti Platter",
    "셰프 코스":    "Fine Dining",
    "샐러드":       "Salad",
    "주스":         "Juice",
}

# API 결과 캐시
_mealdb_cache:     dict[str, str | None] = {}
_cocktaildb_cache: dict[str, str | None] = {}


def fetch_mealdb_url(query: str) -> str | None:
    """MealDB 검색 → 첫 번째 결과의 이미지 URL"""
    if query in _mealdb_cache:
        return _mealdb_cache[query]
    try:
        resp = requests.get(
            f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}",
            timeout=10,
        )
        meals = (resp.json().get("meals") or [])
        url = meals[0]["strMealThumb"] if meals else None
        _mealdb_cache[query] = url
        return url
    except Exception:
        _mealdb_cache[query] = None
        return None


def fetch_cocktaildb_url(query: str) -> str | None:
    """TheCocktailDB 검색 → 첫 번째 결과의 이미지 URL"""
    if query in _cocktaildb_cache:
        return _cocktaildb_cache[query]
    try:
        resp = requests.get(
            f"https://www.thecocktaildb.com/api/json/v1/1/search.php?s={query}",
            timeout=10,
        )
        drinks = (resp.json().get("drinks") or [])
        url = drinks[0]["strDrinkThumb"] if drinks else None
        _cocktaildb_cache[query] = url
        return url
    except Exception:
        _cocktaildb_cache[query] = None
        return None


def download_bytes(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=15)
        ct = resp.headers.get("content-type", "")
        if resp.status_code == 200 and "image" in ct:
            return resp.content
    except Exception:
        pass
    return None


class Command(BaseCommand):
    help = "메뉴별 이미지를 저장합니다 (음료=CocktailDB, 음식=MealDB)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="기존 이미지도 덮어씁니다.")

    def handle(self, *args, **options):
        reset = options["reset"]

        # ── 1단계: 모든 고유 URL 수집 ─────────────────────────────────
        self.stdout.write("\n🔍 이미지 URL 수집 중...\n")

        menu_names = list(
            MenuItem.objects.values_list("name", flat=True).distinct()
        )

        url_map: dict[str, str] = {}

        for name in menu_names:
            # ① Wikipedia Commons 직접 URL 우선
            if name in DIRECT_URLS:
                url_map[name] = DIRECT_URLS[name]
                continue

            # ② TheCocktailDB (음료류)
            cdb_query = COCKTAILDB_SEARCH.get(name)
            if cdb_query:
                cdb_url = fetch_cocktaildb_url(cdb_query)
                if cdb_url:
                    url_map[name] = cdb_url
                    self.stdout.write(f"  🍹 [{name}] → CocktailDB: {cdb_query}")
                    time.sleep(0.25)
                    continue

            # ③ MealDB (조리 음식 / 사이드)
            mdb_query = MEALDB_SEARCH.get(name)
            if mdb_query:
                mdb_url = fetch_mealdb_url(mdb_query)
                if mdb_url:
                    url_map[name] = mdb_url
                    self.stdout.write(f"  🍽️  [{name}] → MealDB: {mdb_query}")
                    time.sleep(0.25)
                    continue

            self.stdout.write(self.style.WARNING(f"  ✗ [{name}] URL 없음 — 건너뜀"))

        self.stdout.write(
            self.style.SUCCESS(f"\n  → {len(url_map)}/{len(menu_names)}개 메뉴 URL 확보\n")
        )

        # ── 2단계: 이미지 다운로드 (URL 중복 제거) ────────────────────
        self.stdout.write("📥 이미지 다운로드 중...")
        bytes_cache: dict[str, bytes | None] = {}
        unique_urls = set(url_map.values())

        for i, url in enumerate(unique_urls, 1):
            data = download_bytes(url)
            bytes_cache[url] = data
            status = "✓" if data else "✗ 실패"
            short = url[:70]
            self.stdout.write(f"  [{i:02d}/{len(unique_urls)}] {status}  {short}")
            time.sleep(0.1)

        ok = sum(1 for v in bytes_cache.values() if v)
        self.stdout.write(self.style.SUCCESS(f"\n  → {ok}/{len(unique_urls)}개 다운로드 완료\n"))

        # ── 3단계: DB 저장 ─────────────────────────────────────────────
        self.stdout.write("💾 메뉴 아이템에 이미지 저장 중...")
        qs = MenuItem.objects.all() if reset else MenuItem.objects.filter(image="")
        total  = qs.count()
        saved  = skipped = failed = 0

        for item in qs.iterator():
            url = url_map.get(item.name)
            if not url:
                skipped += 1
                continue
            data = bytes_cache.get(url)
            if not data:
                failed += 1
                continue
            try:
                item.image.save(f"menu_{item.pk}.jpg", ContentFile(data), save=True)
                saved += 1
            except Exception as e:
                self.stderr.write(f"  저장 오류 ({item.name}): {e}")
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ 완료! 저장 {saved}개 / URL없음 {skipped}개 / 실패 {failed}개 (전체 {total}개)"
        ))
