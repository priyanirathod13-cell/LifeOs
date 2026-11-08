from datetime import date, datetime, timedelta
import zoneinfo
from django.conf import settings
from django.utils import timezone


def get_user_today(user=None) -> date:
    """
    Returns today's date in the user's configured timezone (or settings.TIME_ZONE).
    """
    user_tz_name = getattr(user, 'timezone', None) or settings.TIME_ZONE
    try:
        user_tz = zoneinfo.ZoneInfo(user_tz_name)
    except Exception:
        user_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
    return timezone.now().astimezone(user_tz).date()


def parse_date_range(user, query_params) -> dict:
    """
    Parses and validates date filter parameters from request.GET.
    Supported presets: '7d' (default), '30d', '90d', 'this_week', 'this_month', 'custom'.

    Returns a structured dictionary:
    {
        'start_date': date,
        'end_date': date,
        'preset': str,
        'label': str,
        'days_count': int,
        'prev_start_date': date,
        'prev_end_date': date,
        'prev_label': str,
    }
    """
    today = get_user_today(user)
    preset = query_params.get('range', '7d').lower()

    if preset == '30d':
        start_date = today - timedelta(days=29)
        end_date = today
        label = 'Last 30 Days'
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date - timedelta(days=1)
        prev_label = 'Prior 30 Days'
    elif preset == '90d':
        start_date = today - timedelta(days=89)
        end_date = today
        label = 'Last 90 Days'
        prev_start = start_date - timedelta(days=90)
        prev_end = start_date - timedelta(days=1)
        prev_label = 'Prior 90 Days'
    elif preset == 'this_week':
        # Monday to Sunday of current week
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        label = 'This Week'
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)
        prev_label = 'Last Week'
    elif preset == 'this_month':
        start_date = date(today.year, today.month, 1)
        # End of current month or today
        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)
        end_date = next_month - timedelta(days=1)
        label = today.strftime('%B %Y')
        # Previous month
        if today.month == 1:
            prev_start = date(today.year - 1, 12, 1)
            prev_end = date(today.year, 1, 1) - timedelta(days=1)
        else:
            prev_start = date(today.year, today.month - 1, 1)
            prev_end = date(today.year, today.month, 1) - timedelta(days=1)
        prev_label = prev_start.strftime('%B %Y')
    elif preset == 'custom':
        raw_start = query_params.get('date_from', '').strip()
        raw_end = query_params.get('date_to', '').strip()
        parsed_start = None
        parsed_end = None
        if raw_start:
            try:
                parsed_start = datetime.strptime(raw_start, '%Y-%m-%d').date()
            except ValueError:
                pass
        if raw_end:
            try:
                parsed_end = datetime.strptime(raw_end, '%Y-%m-%d').date()
            except ValueError:
                pass

        if parsed_start and parsed_end and parsed_start <= parsed_end:
            start_date = parsed_start
            end_date = parsed_end
            label = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"
            span = (end_date - start_date).days + 1
            prev_start = start_date - timedelta(days=span)
            prev_end = start_date - timedelta(days=1)
            prev_label = f"Prior {span} Days"
        elif parsed_start:
            start_date = parsed_start
            end_date = today
            label = f"Since {start_date.strftime('%d %b %Y')}"
            span = (end_date - start_date).days + 1
            prev_start = start_date - timedelta(days=span)
            prev_end = start_date - timedelta(days=1)
            prev_label = f"Prior {span} Days"
        else:
            # Fallback to 7d
            preset = '7d'
            start_date = today - timedelta(days=6)
            end_date = today
            label = 'Last 7 Days'
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
            prev_label = 'Prior 7 Days'
    else:
        # Default '7d'
        preset = '7d'
        start_date = today - timedelta(days=6)
        end_date = today
        label = 'Last 7 Days'
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)
        prev_label = 'Prior 7 Days'

    days_count = max(1, (end_date - start_date).days + 1)

    return {
        'start_date': start_date,
        'end_date': end_date,
        'preset': preset,
        'label': label,
        'days_count': days_count,
        'prev_start_date': prev_start,
        'prev_end_date': prev_end,
        'prev_label': prev_label,
    }
