"""
config/db_router.py

프록시 VIP 기반 Read/Write DB 분기 라우터.

- db_for_read  → 'readonly' DB (프록시가 replica로 라우팅)
- db_for_write → 'default'  DB (프록시가 primary로 라우팅)
- migrate는 'default' DB에만 적용

코드에서 직접 DB를 지정하고 싶을 때:
    MyModel.objects.using('readonly').filter(...)
    MyModel.objects.using('default').create(...)
"""


class ReadWriteRouter:
    """
    모든 read 쿼리를 'readonly' 커넥션으로,
    write 쿼리 및 migrate는 'default' 커넥션으로 보냅니다.
    """

    def db_for_read(self, model, **hints):
        """SELECT 쿼리 → readonly DB"""
        return 'readonly'

    def db_for_write(self, model, **hints):
        """INSERT / UPDATE / DELETE 쿼리 → default DB"""
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """두 DB 간 외래키 관계 허용 (같은 물리 DB를 바라보므로 허용)"""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """마이그레이션은 default DB에만 적용"""
        return db == 'default'
