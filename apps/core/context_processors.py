from apps.core.models import UserPreference
from apps.core.services.notification_service import NotificationService


def lifeos_core_context(request):
    """
    Context processor providing global variables for LifeOS:
    - unread_notifications_count: Count of unread notifications for badge
    - recent_notifications: Latest 5 notifications for dropdown
    - user_preferences: UserPreference object
    """
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
            'user_preferences': None,
        }

    # Automatically generate proactive notifications periodically or on visit
    try:
        NotificationService.generate_system_notifications(request.user)
    except Exception:
        pass

    unread_count = NotificationService.get_unread_count(request.user)
    recent = NotificationService.get_recent(request.user, limit=5)
    prefs = UserPreference.get_for_user(request.user)

    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent,
        'user_preferences': prefs,
    }
