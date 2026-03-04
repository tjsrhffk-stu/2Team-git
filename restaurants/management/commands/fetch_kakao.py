"""
카카오 로컬 API를 사용해 서울 주요 지역 맛집 데이터를 DB에 저장하는 관리 커맨드.

사용법:
    python manage.py fetch_kakao           # 기본 (전체 지역)
    python manage.py fetch_kakao --area 강남  # 특정 지역만
    python manage.py fetch_kakao --limit 5    # 지역당 최대 5페이지
"""

import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from restaurants.models import Restaurant, Category

# ── 서울 주요 지역 좌표 (lng, lat 순서 — 카카오 API는 x=경도, y=위도) ──
AREAS = {
    "홍대":    (126.9235, 37.5563),
    "강남":    (127.0276, 37.4979),
    "이태원":  (126.9942, 37.5340),
    "명동":    (126.9869, 37.5636),
    "신촌":    (126.9368, 37.5551),
    "건대입구": (127.0703, 37.5407),
    "성수":    (127.0559, 37.5445),
    "종로":    (126.9823, 37.5704),
    "여의도":  (126.9244, 37.5215),
    "마포":    (126.9086, 37.5549),
    "인사동":  (126.9856, 37.5736),
    "압구정":  (127.0291, 37.5272),
    "잠실":    (127.1000, 37.5132),
    "신림":    (126.9293, 37.4843),
    "대학로":  (127.0024, 37.5836),
    "동대문":  (127.0097, 37.5711),
    "서울숲":  (127.0448, 37.5437),
    "망원":    (126.9018, 37.5566),
    "판교":    (127.1113, 37.3947),
    "수서":    (127.1023, 37.4866),
}

# ── 카카오 카테고리 코드 ──
# FD6 = 음식점, CE7 = 카페
CATEGORY_CODES = ["FD6", "CE7"]

# ── 카카오 category_name → 우리 Category 이름 매핑 ──
CATEGORY_MAP = [
    ("한식",   "한식"),
    ("일식",   "일식"),
    ("중식",   "중식"),
    ("양식",   "양식"),
    ("카페",   "카페"),
    ("커피",   "카페"),
    ("패스트푸드", "패스트푸드"),
    ("분식",   "한식"),
    ("치킨",   "한식"),
    ("곱창",   "한식"),
    ("해산물",  "한식"),
    ("국밥",   "한식"),
    ("삼겹살", "한식"),
    ("갈비",   "한식"),
    ("냉면",   "한식"),
    ("초밥",   "일식"),
    ("라멘",   "일식"),
    ("우동",   "일식"),
    ("피자",   "양식"),
    ("스테이크", "양식"),
    ("파스타",  "양식"),
    ("버거",   "패스트푸드"),
    ("맥도날드", "패스트푸드"),
    ("롯데리아", "패스트푸드"),
]


def _map_category(kakao_cat_name: str) -> str:
    """카카오 카테고리 문자열 → 우리 카테고리 이름"""
    for keyword, our_cat in CATEGORY_MAP:
        if keyword in kakao_cat_name:
            return our_cat
    return "기타"


def _get_or_create_category(name: str) -> Category:
    cat, _ = Category.objects.get_or_create(name=name)
    return cat


def fetch_places(api_key: str, x: float, y: float, category_code: str, page: int = 1):
    """카카오 로컬 카테고리 검색 API 호출"""
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "category_group_code": category_code,
        "x": x,
        "y": y,
        "radius": 1500,   # 반경 1.5km
        "size": 15,       # 페이지당 최대 15개
        "page": page,
        "sort": "distance",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


class Command(BaseCommand):
    help = "카카오 로컬 API로 서울 맛집 데이터를 DB에 저장합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--area", type=str, default=None,
            help="특정 지역만 검색 (예: 강남, 홍대). 미지정 시 전체 지역."
        )
        parser.add_argument(
            "--limit", type=int, default=3,
            help="지역별 최대 페이지 수 (기본 3 = 최대 45개/지역)"
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "KAKAO_REST_API_KEY", "")
        if not api_key:
            self.stderr.write(self.style.ERROR("KAKAO_REST_API_KEY가 설정되지 않았습니다. .env를 확인하세요."))
            return

        area_filter = options["area"]
        max_pages   = options["limit"]

        areas = AREAS
        if area_filter:
            if area_filter not in AREAS:
                self.stderr.write(self.style.ERROR(f"알 수 없는 지역: {area_filter}. 가능한 지역: {', '.join(AREAS)}"))
                return
            areas = {area_filter: AREAS[area_filter]}

        # 중복 방지용 세트 (이름+주소)
        seen = set(
            Restaurant.objects.values_list("name", "address")
        )

        total_created = 0
        total_skipped = 0

        for area_name, (x, y) in areas.items():
            self.stdout.write(f"\n📍 [{area_name}] 검색 중 (좌표: {x}, {y})")

            for code in CATEGORY_CODES:
                area_created = 0

                for page in range(1, max_pages + 1):
                    try:
                        data = fetch_places(api_key, x, y, code, page)
                    except requests.HTTPError as e:
                        self.stderr.write(f"  API 오류: {e}")
                        break
                    except Exception as e:
                        self.stderr.write(f"  네트워크 오류: {e}")
                        break

                    documents = data.get("documents", [])
                    if not documents:
                        break  # 더 이상 결과 없음

                    for place in documents:
                        name    = place.get("place_name", "").strip()
                        address = (place.get("road_address_name") or place.get("address_name", "")).strip()
                        phone   = place.get("phone", "").strip()
                        website = place.get("place_url", "").strip()
                        lng_str = place.get("x", "")
                        lat_str = place.get("y", "")
                        kakao_cat = place.get("category_name", "")

                        if not name or not address:
                            continue

                        # 중복 체크
                        key = (name, address)
                        if key in seen:
                            total_skipped += 1
                            continue
                        seen.add(key)

                        # 카테고리 매핑
                        our_cat_name = _map_category(kakao_cat)
                        category = _get_or_create_category(our_cat_name)

                        # 좌표
                        try:
                            lat = float(lat_str)
                            lng = float(lng_str)
                        except (ValueError, TypeError):
                            lat, lng = None, None

                        # Restaurant 생성
                        # owner=None: 사장님 없이 공개 데이터로 등록
                        try:
                            rest = Restaurant(
                                name=name,
                                address=address,
                                phone=phone,
                                website=website,
                                lat=lat,
                                lng=lng,
                                category=category,
                                description=f"카카오 데이터 | {kakao_cat}",
                                owner=None,
                            )
                            # save() 오버라이드가 lat/lng 있으면 지오코딩 안 함
                            rest.save()
                            area_created += 1
                            total_created += 1
                        except Exception as e:
                            self.stderr.write(f"  저장 실패 ({name}): {e}")
                            continue

                    # 마지막 페이지 확인
                    meta = data.get("meta", {})
                    if meta.get("is_end", True):
                        break

                    # API 레이트리밋 방지
                    time.sleep(0.3)

                self.stdout.write(
                    f"  {'음식점' if code=='FD6' else '카페'}: {area_created}개 등록"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ 완료! 총 {total_created}개 등록 / {total_skipped}개 중복 스킵"
        ))
