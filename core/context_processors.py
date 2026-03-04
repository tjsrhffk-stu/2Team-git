from .models import Notification


def notifications(request):
    """로그인 사용자의 읽지 않은 알림 수를 모든 템플릿에 제공"""
    if request.user.is_authenticated:
        unread = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        recent_notifications = Notification.objects.filter(
            recipient=request.user
        )[:10]
    else:
        unread = 0
        recent_notifications = []
    return {
        "unread_notification_count": unread,
        "recent_notifications": recent_notifications,
    }
