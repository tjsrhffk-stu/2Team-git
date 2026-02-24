from django.contrib import admin
from .models import Restaurant # 실제 모델 클래스 이름

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    # 관리자 목록에서 보여줄 필드들
    list_display = ('id', 'name', 'address', 'lat', 'lng')
    
    # 클릭해서 수정 페이지로 들어갈 필드
    list_display_links = ('id', 'name')
    
    # 검색 기능 (이름이나 주소로 검색 가능)
    search_fields = ('name', 'address')

    # 위도, 경도 필드는 수동으로 넣기 힘들 수 있으니 그룹화해서 보여줌
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'description', 'address')
        }),
        ('위치 정보 (직접 입력 테스트)', {
            'fields': ('lat', 'lng'),
            'description': '테스트를 위해 위도(lat)와 경도(lng)를 직접 입력해보세요.'
        }),
    )