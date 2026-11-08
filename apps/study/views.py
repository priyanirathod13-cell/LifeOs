from datetime import date, datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, F, Q, Sum, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ExamForm,
    RevisionForm,
    StudyPlanForm,
    StudySessionForm,
    SubjectForm,
    TopicForm,
)
from .models import (
    Exam,
    ExamStatus,
    ExamType,
    PlanStatus,
    Priority,
    Revision,
    RevisionStatus,
    SessionType,
    StudyPlan,
    StudySession,
    Subject,
    SubjectStatus,
    SubjectType,
    Topic,
    TopicStatus,
)


def format_duration(total_minutes):
    """Formats minutes into human-readable duration."""
    if not total_minutes:
        return "0 mins"
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    return f"{mins} mins"


# ==============================================================================
# 1. STUDY DASHBOARD
# ==============================================================================

@login_required
def study_dashboard_view(request):
    """
    Central academic & study dashboard aggregating subjects, topics,
    syllabus completion, weekly/monthly study duration, and upcoming exams.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()

    # Time boundaries
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # 1. Metric Cards
    subjects_qs = Subject.objects.filter(user=user)
    total_subjects = subjects_qs.count()
    active_subjects = subjects_qs.filter(status=SubjectStatus.ACTIVE).count()

    topics_qs = Topic.objects.filter(subject__user=user)
    total_topics = topics_qs.count()
    completed_topics = topics_qs.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()
    overall_syllabus_pct = round((completed_topics / total_topics) * 100) if total_topics > 0 else 0

    week_minutes = StudySession.objects.filter(
        user=user,
        session_date__gte=start_of_week,
        session_date__lte=today,
        duration_minutes__isnull=False
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    month_minutes = StudySession.objects.filter(
        user=user,
        session_date__gte=start_of_month,
        session_date__lte=today,
        duration_minutes__isnull=False
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    upcoming_exams_qs = Exam.objects.filter(
        user=user,
        status=ExamStatus.UPCOMING,
        exam_date__gte=today
    ).select_related('subject').order_by('exam_date')
    upcoming_exams_count = upcoming_exams_qs.count()

    pending_revisions_qs = Revision.objects.filter(
        user=user,
        status=RevisionStatus.PENDING
    ).select_related('subject', 'topic')
    pending_revisions_count = pending_revisions_qs.count()

    # 2. Today's Planned Sessions
    today_plans = StudyPlan.objects.filter(
        user=user,
        planned_date=today
    ).select_related('subject', 'topic').order_by('status', 'preferred_time', '-priority')

    # 3. Active Session (if any)
    active_session = StudySession.objects.filter(
        user=user,
        end_datetime__isnull=True,
        start_datetime__isnull=False
    ).select_related('subject', 'topic').first()

    # 4. Incomplete / Falling-Behind Subjects
    incomplete_subjects_data = []
    for subj in subjects_qs.filter(status=SubjectStatus.ACTIVE).prefetch_related('topics'):
        t_count = subj.topics.count()
        c_count = subj.topics.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()
        pct = round((c_count / t_count) * 100) if t_count > 0 else 0
        is_behind = bool(subj.target_date and subj.target_date < today and pct < 100)

        if pct < 100 or is_behind:
            incomplete_subjects_data.append({
                'subject': subj,
                'total_topics': t_count,
                'completed_topics': c_count,
                'pct': pct,
                'is_behind': is_behind,
            })
    incomplete_subjects_data.sort(key=lambda x: (not x['is_behind'], x['pct']))

    # 5. Recent Study Activity
    recent_sessions = StudySession.objects.filter(
        user=user,
        duration_minutes__isnull=False
    ).select_related('subject', 'topic').order_by('-session_date', '-created_at')[:6]

    # 6. Weekly Study Progress (Last 7 Days Chart Data)
    weekly_chart_data = []
    for day_offset in range(6, -1, -1):
        target_day = today - timedelta(days=day_offset)
        day_mins = StudySession.objects.filter(
            user=user,
            session_date=target_day,
            duration_minutes__isnull=False
        ).aggregate(total=Sum('duration_minutes'))['total'] or 0
        weekly_chart_data.append({
            'day_name': target_day.strftime('%a'),
            'date': target_day,
            'minutes': day_mins,
            'hours': round(day_mins / 60, 1),
            'formatted': format_duration(day_mins),
            'is_today': target_day == today,
        })

    max_day_mins = max([d['minutes'] for d in weekly_chart_data] + [60])
    for d in weekly_chart_data:
        d['height_pct'] = round((d['minutes'] / max_day_mins) * 100) if max_day_mins > 0 else 0

    context = {
        'page_title': 'Study Dashboard',
        'active_nav': 'study',
        'today': today,

        # Metrics
        'total_subjects': total_subjects,
        'active_subjects': active_subjects,
        'total_topics': total_topics,
        'completed_topics': completed_topics,
        'overall_syllabus_pct': overall_syllabus_pct,
        'week_duration_str': format_duration(week_minutes),
        'month_duration_str': format_duration(month_minutes),
        'upcoming_exams_count': upcoming_exams_count,
        'pending_revisions_count': pending_revisions_count,

        # Sections
        'today_plans': today_plans,
        'active_session': active_session,
        'upcoming_exams': upcoming_exams_qs[:4],
        'incomplete_subjects': incomplete_subjects_data[:5],
        'recent_sessions': recent_sessions,
        'weekly_chart_data': weekly_chart_data,
    }
    return render(request, 'study/dashboard.html', context)


# ==============================================================================
# 2. SUBJECT MANAGEMENT VIEWS
# ==============================================================================

@login_required
def subject_list_view(request):
    """
    Display user subjects with search, status filtering, and syllabus progress.
    """
    user = request.user
    qs = Subject.objects.filter(user=user).annotate(
        topics_count=Count('topics'),
        completed_count=Count(
            'topics',
            filter=Q(topics__status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED])
        )
    )

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(description__icontains=q))

    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in SubjectStatus.values:
        qs = qs.filter(status=status_filter)

    # Type filter
    type_filter = request.GET.get('type', '').strip()
    if type_filter and type_filter in SubjectType.values:
        qs = qs.filter(subject_type=type_filter)

    # Sorting
    sort = request.GET.get('sort', 'name')
    if sort == 'topics':
        qs = qs.order_by('-topics_count')
    elif sort == 'recent':
        qs = qs.order_by('-created_at')
    elif sort == 'target_date':
        qs = qs.order_by('target_date', 'name')
    else:
        qs = qs.order_by('name')

    subjects_data = []
    for s in qs:
        t_count = s.topics_count
        c_count = s.completed_count
        pct = round((c_count / t_count) * 100) if t_count > 0 else 0
        mins = StudySession.objects.filter(user=user, subject=s, duration_minutes__isnull=False).aggregate(total=Sum('duration_minutes'))['total'] or 0

        subjects_data.append({
            'subject': s,
            'total_topics': t_count,
            'completed_topics': c_count,
            'progress_pct': pct,
            'study_duration_str': format_duration(mins),
        })

    context = {
        'page_title': 'Subjects & Courses',
        'active_nav': 'study',
        'subjects_data': subjects_data,
        'total_count': Subject.objects.filter(user=user).count(),
        'q': q,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'sort': sort,
        'statuses': SubjectStatus.choices,
        'types': SubjectType.choices,
    }
    return render(request, 'study/subjects.html', context)


@login_required
def subject_create_view(request):
    """
    Add a new learning subject.
    """
    if request.method == 'POST':
        form = SubjectForm(request.POST, user=request.user)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f"Subject '{subject.name}' added successfully.")
            return redirect('study:subject_detail', pk=subject.pk)
    else:
        form = SubjectForm(user=request.user)

    context = {
        'page_title': 'Add New Subject',
        'active_nav': 'study',
        'form': form,
    }
    return render(request, 'study/subject_form.html', context)


@login_required
def subject_detail_view(request, pk):
    """
    Subject details: syllabus progress, chapters/topics, upcoming exams,
    and logged study sessions.
    """
    user = request.user
    subject = get_object_or_404(Subject, pk=pk, user=user)

    topics = subject.topics.all().order_by('chapter', 'order', 'created_at')
    total_topics = topics.count()
    completed_topics = topics.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()
    in_progress_topics = topics.filter(status=TopicStatus.IN_PROGRESS).count()
    progress_pct = round((completed_topics / total_topics) * 100) if total_topics > 0 else 0

    # Group topics by chapter
    chapters_dict = {}
    for t in topics:
        chap_name = t.chapter.strip() if t.chapter else "General Topics"
        if chap_name not in chapters_dict:
            chapters_dict[chap_name] = []
        chapters_dict[chap_name].append(t)

    # Exams for this subject
    exams = subject.exams.filter(user=user).order_by('exam_date')

    # Study Sessions for this subject
    sessions = subject.sessions.filter(user=user, duration_minutes__isnull=False).select_related('topic').order_by('-session_date', '-created_at')[:8]
    total_study_mins = subject.sessions.filter(user=user, duration_minutes__isnull=False).aggregate(total=Sum('duration_minutes'))['total'] or 0

    context = {
        'page_title': subject.name,
        'active_nav': 'study',
        'subject': subject,
        'topics': topics,
        'chapters_dict': chapters_dict,
        'total_topics': total_topics,
        'completed_topics': completed_topics,
        'in_progress_topics': in_progress_topics,
        'progress_pct': progress_pct,
        'exams': exams,
        'sessions': sessions,
        'study_duration_str': format_duration(total_study_mins),
    }
    return render(request, 'study/subject_detail.html', context)


@login_required
def subject_update_view(request, pk):
    """
    Update subject information.
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)

    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Subject '{subject.name}' updated.")
            return redirect('study:subject_detail', pk=subject.pk)
    else:
        form = SubjectForm(instance=subject, user=request.user)

    context = {
        'page_title': f"Edit Subject — {subject.name}",
        'active_nav': 'study',
        'form': form,
        'subject': subject,
    }
    return render(request, 'study/subject_form.html', context)


@login_required
def subject_delete_view(request, pk):
    """
    Delete a subject with confirmation.
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)

    if request.method == 'POST':
        name = subject.name
        subject.delete()
        messages.success(request, f"Subject '{name}' was deleted.")
        return redirect('study:subject_list')

    context = {
        'page_title': f"Delete Subject — {subject.name}",
        'active_nav': 'study',
        'subject': subject,
        'topics_count': subject.topics.count(),
        'sessions_count': subject.sessions.count(),
    }
    return render(request, 'study/subject_confirm_delete.html', context)


# ==============================================================================
# 3. TOPICS & CHAPTER MANAGEMENT VIEWS
# ==============================================================================

@login_required
def topic_list_view(request):
    """
    List of topics filterable by subject, chapter, and completion status.
    """
    user = request.user
    qs = Topic.objects.filter(subject__user=user).select_related('subject')

    subject_filter = request.GET.get('subject', '').strip()
    if subject_filter and subject_filter.isdigit():
        qs = qs.filter(subject_id=int(subject_filter))

    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in TopicStatus.values:
        qs = qs.filter(status=status_filter)

    priority_filter = request.GET.get('priority', '').strip()
    if priority_filter and priority_filter in Priority.values:
        qs = qs.filter(priority=priority_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(chapter__icontains=q) | Q(description__icontains=q))

    topics = qs.order_by('subject__name', 'chapter', 'order', 'created_at')
    user_subjects = Subject.objects.filter(user=user).order_by('name')

    context = {
        'page_title': 'Topics & Chapters',
        'active_nav': 'study',
        'topics': topics,
        'user_subjects': user_subjects,
        'subject_filter': int(subject_filter) if subject_filter.isdigit() else None,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'q': q,
        'statuses': TopicStatus.choices,
        'priorities': Priority.choices,
    }
    return render(request, 'study/topics.html', context)


@login_required
def topic_create_view(request):
    """
    Create a new topic. Accepts optional ?subject=<id> query parameter.
    """
    initial = {}
    subj_id = request.GET.get('subject', '').strip()
    if subj_id and subj_id.isdigit():
        subj = Subject.objects.filter(id=int(subj_id), user=request.user).first()
        if subj:
            initial['subject'] = subj.pk

    if request.method == 'POST':
        form = TopicForm(request.POST, user=request.user)
        if form.is_valid():
            topic = form.save()
            messages.success(request, f"Topic '{topic.title}' added to {topic.subject.name}.")
            return redirect('study:subject_detail', pk=topic.subject.pk)
    else:
        form = TopicForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Add Topic',
        'active_nav': 'study',
        'form': form,
    }
    return render(request, 'study/topic_form.html', context)


@login_required
def topic_update_view(request, pk):
    """
    Update topic attributes, chapter, priority, and progress notes.
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)

    if request.method == 'POST':
        form = TopicForm(request.POST, instance=topic, user=request.user)
        if form.is_valid():
            t = form.save()
            messages.success(request, f"Topic '{t.title}' updated.")
            return redirect('study:subject_detail', pk=t.subject.pk)
    else:
        form = TopicForm(instance=topic, user=request.user)

    context = {
        'page_title': f"Edit Topic — {topic.title}",
        'active_nav': 'study',
        'form': form,
        'topic': topic,
    }
    return render(request, 'study/topic_form.html', context)


@login_required
def topic_delete_view(request, pk):
    """
    Delete topic with confirmation.
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    subject_pk = topic.subject.pk

    if request.method == 'POST':
        title = topic.title
        topic.delete()
        messages.success(request, f"Topic '{title}' was deleted.")
        return redirect('study:subject_detail', pk=subject_pk)

    context = {
        'page_title': f"Delete Topic — {topic.title}",
        'active_nav': 'study',
        'topic': topic,
    }
    return render(request, 'study/topic_confirm_delete.html', context)


@login_required
@require_POST
def topic_toggle_complete_view(request, pk):
    """
    Quickly toggle topic between Completed and Not Started / In Progress.
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    if topic.status in [TopicStatus.COMPLETED, TopicStatus.MASTERED]:
        topic.status = TopicStatus.IN_PROGRESS
        topic.completion_date = None
        messages.info(request, f"Topic '{topic.title}' marked In Progress.")
    else:
        topic.status = TopicStatus.COMPLETED
        topic.completion_date = timezone.now().date()
        messages.success(request, f"Topic '{topic.title}' marked Completed!")
    topic.save()

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'study:subject_detail', pk=topic.subject.pk)


# ==============================================================================
# 4. SYLLABUS TRACKER VIEW
# ==============================================================================

@login_required
def syllabus_tracker_view(request):
    """
    Visual syllabus progress tracker across all subjects.
    Computes subject completion rates, overall mastery, and highlights
    subjects falling behind target completion dates.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()

    subjects = Subject.objects.filter(user=user).prefetch_related('topics').order_by('status', 'name')

    total_topics_all = 0
    completed_topics_all = 0

    subjects_progress = []
    for s in subjects:
        topics_list = list(s.topics.all().order_by('chapter', 'order', 'title'))
        t_count = len(topics_list)
        c_count = sum(1 for t in topics_list if t.status in [TopicStatus.COMPLETED, TopicStatus.MASTERED])
        ip_count = sum(1 for t in topics_list if t.status == TopicStatus.IN_PROGRESS)
        ns_count = sum(1 for t in topics_list if t.status == TopicStatus.NOT_STARTED)
        pct = round((c_count / t_count) * 100) if t_count > 0 else 0

        is_behind = bool(s.target_date and s.target_date < today and pct < 100)
        days_left = (s.target_date - today).days if s.target_date else None

        total_topics_all += t_count
        completed_topics_all += c_count

        subjects_progress.append({
            'subject': s,
            'topics': topics_list,
            'total_count': t_count,
            'completed_count': c_count,
            'in_progress_count': ip_count,
            'not_started_count': ns_count,
            'progress_pct': pct,
            'is_behind': is_behind,
            'days_left': days_left,
        })

    overall_pct = round((completed_topics_all / total_topics_all) * 100) if total_topics_all > 0 else 0

    context = {
        'page_title': 'Syllabus Tracker',
        'active_nav': 'study',
        'subjects_progress': subjects_progress,
        'total_topics_all': total_topics_all,
        'completed_topics_all': completed_topics_all,
        'overall_pct': overall_pct,
        'today': today,
    }
    return render(request, 'study/syllabus.html', context)


# ==============================================================================
# 5. STUDY PLANNER VIEWS
# ==============================================================================

@login_required
def study_planner_view(request):
    """
    Study planner interface organized by temporal scopes (Today, Upcoming, Weekly, Past).
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    qs = StudyPlan.objects.filter(user=user).select_related('subject', 'topic')

    tab = request.GET.get('tab', 'today').strip()

    if tab == 'today':
        plans = qs.filter(planned_date=today).order_by('status', 'preferred_time', '-priority')
    elif tab == 'upcoming':
        plans = qs.filter(planned_date__gt=today).order_by('planned_date', 'preferred_time', '-priority')
    elif tab == 'week':
        plans = qs.filter(planned_date__gte=start_of_week, planned_date__lte=end_of_week).order_by('planned_date', 'preferred_time')
    elif tab == 'past':
        plans = qs.filter(planned_date__lt=today).order_by('-planned_date', 'preferred_time')
    else:
        # All plans
        plans = qs.order_by('-planned_date', 'preferred_time')

    # Summary metrics
    today_count = qs.filter(planned_date=today).count()
    today_completed_count = qs.filter(planned_date=today, status=PlanStatus.COMPLETED).count()
    upcoming_count = qs.filter(planned_date__gt=today, status=PlanStatus.PLANNED).count()

    context = {
        'page_title': 'Study Planner',
        'active_nav': 'study',
        'plans': plans,
        'tab': tab,
        'today': today,
        'today_count': today_count,
        'today_completed_count': today_completed_count,
        'upcoming_count': upcoming_count,
    }
    return render(request, 'study/planner.html', context)


@login_required
def study_plan_create_view(request):
    """
    Schedule a planned study activity.
    """
    initial = {'planned_date': timezone.now().date()}
    subj_id = request.GET.get('subject', '').strip()
    if subj_id and subj_id.isdigit():
        initial['subject'] = int(subj_id)

    if request.method == 'POST':
        form = StudyPlanForm(request.POST, user=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.save()
            messages.success(request, f"Study planned for {plan.subject.name} on {plan.planned_date}.")
            return redirect('study:planner')
    else:
        form = StudyPlanForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Schedule Study Plan',
        'active_nav': 'study',
        'form': form,
    }
    return render(request, 'study/planner_form.html', context)


@login_required
def study_plan_update_view(request, pk):
    """
    Edit planned study activity.
    """
    plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)

    if request.method == 'POST':
        form = StudyPlanForm(request.POST, instance=plan, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Study plan updated.")
            return redirect('study:planner')
    else:
        form = StudyPlanForm(instance=plan, user=request.user)

    context = {
        'page_title': 'Edit Study Plan',
        'active_nav': 'study',
        'form': form,
        'plan': plan,
    }
    return render(request, 'study/planner_form.html', context)


@login_required
def study_plan_delete_view(request, pk):
    """
    Delete study plan with confirmation.
    """
    plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)

    if request.method == 'POST':
        plan.delete()
        messages.success(request, "Study plan removed.")
        return redirect('study:planner')

    context = {
        'page_title': 'Delete Study Plan',
        'active_nav': 'study',
        'plan': plan,
    }
    return render(request, 'study/planner_confirm_delete.html', context)


@login_required
@require_POST
def study_plan_status_view(request, pk):
    """
    Quickly update plan status (Completed, Skipped, Rescheduled).
    """
    plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)
    new_status = request.POST.get('status', '').strip()

    if new_status in PlanStatus.values:
        plan.status = new_status
        # Handle reschedule date if provided
        reschedule_date = request.POST.get('reschedule_date', '').strip()
        if new_status == PlanStatus.RESCHEDULED and reschedule_date:
            try:
                plan.planned_date = datetime.strptime(reschedule_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        plan.save()
        messages.success(request, f"Plan status updated to {plan.get_status_display()}.")

    return redirect('study:planner')


# ==============================================================================
# 6. STUDY SESSIONS VIEWS (TIME TRACKING & LOGS)
# ==============================================================================

@login_required
def study_sessions_view(request):
    """
    Study session management: live stopwatch timer, duration summaries,
    subject filters, and historical logs.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # Active timer
    active_session = StudySession.objects.filter(
        user=user,
        end_datetime__isnull=True,
        start_datetime__isnull=False
    ).select_related('subject', 'topic').first()

    # Durations
    today_minutes = StudySession.objects.filter(
        user=user,
        session_date=today,
        duration_minutes__isnull=False
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    week_minutes = StudySession.objects.filter(
        user=user,
        session_date__gte=start_of_week,
        session_date__lte=today,
        duration_minutes__isnull=False
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    month_minutes = StudySession.objects.filter(
        user=user,
        session_date__gte=start_of_month,
        session_date__lte=today,
        duration_minutes__isnull=False
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    # Query list
    qs = StudySession.objects.filter(
        user=user,
        duration_minutes__isnull=False
    ).select_related('subject', 'topic')

    subject_filter = request.GET.get('subject', '').strip()
    if subject_filter and subject_filter.isdigit():
        qs = qs.filter(subject_id=int(subject_filter))

    date_filter = request.GET.get('date', '').strip()
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            qs = qs.filter(session_date=d)
        except ValueError:
            pass

    # Pagination
    paginator = Paginator(qs.order_by('-session_date', '-created_at'), 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    subjects = Subject.objects.filter(user=user).order_by('name')

    context = {
        'page_title': 'Study Sessions & Time Tracking',
        'active_nav': 'study',
        'active_session': active_session,
        'page_obj': page_obj,
        'sessions': page_obj.object_list,
        'subjects': subjects,
        'today': today,
        'today_duration': format_duration(today_minutes),
        'week_duration': format_duration(week_minutes),
        'month_duration': format_duration(month_minutes),
        'subject_filter': int(subject_filter) if subject_filter.isdigit() else None,
        'date_filter': date_filter,
    }
    return render(request, 'study/sessions.html', context)


@login_required
@require_POST
def study_session_start_view(request):
    """
    Start a live study session timer. Automatically stops and finalizes
    any previously active session first.
    """
    user = request.user
    subject_id = (request.POST.get('subject_id') or request.POST.get('subject') or '').strip()
    topic_id = (request.POST.get('topic_id') or request.POST.get('topic') or '').strip()
    session_type = request.POST.get('session_type', SessionType.THEORY).strip()

    if not subject_id or not subject_id.isdigit():
        messages.error(request, "Please select a valid subject to start studying.")
        return redirect('study:sessions')

    subject = get_object_or_404(Subject, id=int(subject_id), user=user)
    topic = None
    if topic_id and topic_id.isdigit():
        topic = Topic.objects.filter(id=int(topic_id), subject=subject).first()

    now = timezone.now()

    # Automatically close any previous running timer
    active = StudySession.objects.filter(user=user, end_datetime__isnull=True).first()
    if active and active.start_datetime:
        active.end_datetime = now
        active.duration_minutes = max(1, int((now - active.start_datetime).total_seconds() / 60))
        active.save()

    # Create new active study session
    new_session = StudySession.objects.create(
        user=user,
        subject=subject,
        topic=topic,
        session_date=timezone.localtime(now).date(),
        start_time=timezone.localtime(now).time(),
        start_datetime=now,
        end_datetime=None,
        duration_minutes=None,
        session_type=session_type if session_type in SessionType.values else SessionType.THEORY
    )

    messages.success(request, f"Started study timer for '{subject.name}'. Focus mode active!")
    return redirect('study:sessions')


@login_required
@require_POST
def study_session_stop_view(request, pk):
    """
    Stop an active study session and persist elapsed duration in minutes.
    """
    session = get_object_or_404(StudySession, pk=pk, user=request.user)

    if session.end_datetime is None and session.start_datetime:
        now = timezone.now()
        session.end_datetime = now
        session.end_time = timezone.localtime(now).time()
        elapsed_seconds = (now - session.start_datetime).total_seconds()
        session.duration_minutes = max(1, round(elapsed_seconds / 60))

        # Optional focus rating and notes submitted at stop
        focus = request.POST.get('focus_rating', '').strip()
        if focus and focus.isdigit() and 1 <= int(focus) <= 10:
            session.focus_rating = int(focus)
        notes = request.POST.get('notes', '').strip()
        if notes:
            session.notes = notes

        session.save()

        # Cross-module synchronization: update matching StudyPlan
        if session.subject:
            plan_qs = StudyPlan.objects.filter(
                user=request.user,
                subject=session.subject,
                planned_date=session.session_date,
                status=PlanStatus.PLANNED
            )
            if session.topic:
                plan_qs = plan_qs.filter(Q(topic=session.topic) | Q(topic__isnull=True))
            first_plan = plan_qs.first()
            if first_plan:
                first_plan.status = PlanStatus.COMPLETED
                first_plan.save()

        messages.success(request, f"Session completed! Logged {format_duration(session.duration_minutes)} of study.")

    return redirect('study:sessions')


@login_required
def study_session_create_view(request):
    """
    Manually record a completed study session that occurred in the past.
    """
    if request.method == 'POST':
        form = StudySessionForm(request.POST, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.save()

            # Cross-module synchronization: update matching StudyPlan
            if session.subject:
                plan_qs = StudyPlan.objects.filter(
                    user=request.user,
                    subject=session.subject,
                    planned_date=session.session_date,
                    status=PlanStatus.PLANNED
                )
                if session.topic:
                    plan_qs = plan_qs.filter(Q(topic=session.topic) | Q(topic__isnull=True))
                first_plan = plan_qs.first()
                if first_plan:
                    first_plan.status = PlanStatus.COMPLETED
                    first_plan.save()

            messages.success(request, f"Study session for '{session.subject.name}' recorded.")
            return redirect('study:sessions')
    else:
        now = timezone.localtime(timezone.now())
        initial = {
            'session_date': now.date(),
            'start_time': (now - timedelta(minutes=60)).strftime('%H:%M'),
            'end_time': now.strftime('%H:%M'),
            'duration_minutes': 60,
        }
        form = StudySessionForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Record Study Session',
        'active_nav': 'study',
        'form': form,
    }
    return render(request, 'study/session_form.html', context)


@login_required
def study_session_update_view(request, pk):
    """
    Edit recorded study session details.
    """
    session = get_object_or_404(StudySession, pk=pk, user=request.user)

    if request.method == 'POST':
        form = StudySessionForm(request.POST, instance=session, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Study session updated.")
            return redirect('study:sessions')
    else:
        form = StudySessionForm(instance=session, user=request.user)

    context = {
        'page_title': 'Edit Study Session',
        'active_nav': 'study',
        'form': form,
        'session': session,
    }
    return render(request, 'study/session_form.html', context)


@login_required
def study_session_delete_view(request, pk):
    """
    Delete study session log.
    """
    session = get_object_or_404(StudySession, pk=pk, user=request.user)

    if request.method == 'POST':
        session.delete()
        messages.success(request, "Study session deleted.")
        return redirect('study:sessions')

    context = {
        'page_title': 'Delete Study Session',
        'active_nav': 'study',
        'session': session,
    }
    return render(request, 'study/session_confirm_delete.html', context)


# ==============================================================================
# 7. REVISION PLANNER VIEWS
# ==============================================================================

@login_required
def revision_list_view(request):
    """
    Revision management: displays Today's revisions, Upcoming revisions,
    Overdue revisions, and Completed revisions.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()

    qs = Revision.objects.filter(user=user).select_related('subject', 'topic')

    today_revisions = qs.filter(revision_date=today, status=RevisionStatus.PENDING)
    overdue_revisions = qs.filter(revision_date__lt=today, status=RevisionStatus.PENDING).order_by('revision_date')
    upcoming_revisions = qs.filter(revision_date__gt=today, status=RevisionStatus.PENDING).order_by('revision_date')
    completed_revisions = qs.filter(status=RevisionStatus.COMPLETED).order_by('-completed_at', '-revision_date')[:10]

    context = {
        'page_title': 'Revision Planner',
        'active_nav': 'study',
        'today': today,
        'today_revisions': today_revisions,
        'overdue_revisions': overdue_revisions,
        'upcoming_revisions': upcoming_revisions,
        'completed_revisions': completed_revisions,
        'total_pending': today_revisions.count() + overdue_revisions.count() + upcoming_revisions.count(),
    }
    return render(request, 'study/revisions.html', context)


@login_required
def revision_create_view(request):
    """
    Schedule a new revision milestone for a topic.
    """
    initial = {'revision_date': timezone.now().date() + timedelta(days=3)}
    topic_id = request.GET.get('topic', '').strip()
    if topic_id and topic_id.isdigit():
        top = Topic.objects.filter(id=int(topic_id), subject__user=request.user).select_related('subject').first()
        if top:
            initial['topic'] = top.pk
            initial['subject'] = top.subject.pk
            # Auto-calculate revision iteration number
            prev_revs = Revision.objects.filter(user=request.user, topic=top).count()
            initial['revision_number'] = prev_revs + 1

    if request.method == 'POST':
        form = RevisionForm(request.POST, user=request.user)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.user = request.user
            rev.save()
            messages.success(request, f"Revision #{rev.revision_number} scheduled for '{rev.topic.title}' on {rev.revision_date}.")
            return redirect('study:revisions')
    else:
        form = RevisionForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Schedule Revision',
        'active_nav': 'study',
        'form': form,
    }
    return render(request, 'study/revision_form.html', context)


@login_required
@require_POST
def revision_toggle_complete_view(request, pk):
    """
    Mark a revision as completed.
    """
    rev = get_object_or_404(Revision, pk=pk, user=request.user)
    if rev.status == RevisionStatus.COMPLETED:
        rev.status = RevisionStatus.PENDING
        rev.completed_at = None
        messages.info(request, f"Revision #{rev.revision_number} marked Pending.")
    else:
        rev.status = RevisionStatus.COMPLETED
        rev.completed_at = timezone.now()
        messages.success(request, f"Revision #{rev.revision_number} for '{rev.topic.title}' completed!")
    rev.save()

    return redirect('study:revisions')


@login_required
@require_POST
def revision_reschedule_view(request, pk):
    """
    Reschedule a revision to a new date.
    """
    rev = get_object_or_404(Revision, pk=pk, user=request.user)
    new_date = request.POST.get('revision_date', '').strip()

    if new_date:
        try:
            rev.revision_date = datetime.strptime(new_date, '%Y-%m-%d').date()
            rev.status = RevisionStatus.PENDING
            rev.save()
            messages.success(request, f"Revision #{rev.revision_number} rescheduled to {rev.revision_date}.")
        except ValueError:
            messages.error(request, "Invalid date format.")

    return redirect('study:revisions')


@login_required
def revision_delete_view(request, pk):
    """
    Delete scheduled revision.
    """
    rev = get_object_or_404(Revision, pk=pk, user=request.user)

    if request.method == 'POST':
        rev.delete()
        messages.success(request, "Revision removed.")
        return redirect('study:revisions')

    context = {
        'page_title': 'Delete Revision',
        'active_nav': 'study',
        'revision': rev,
    }
    return render(request, 'study/revision_confirm_delete.html', context)


# ==============================================================================
# 8. EXAMS AND ASSESSMENTS VIEWS
# ==============================================================================

@login_required
def exam_list_view(request):
    """
    Examination & assessment management: displays upcoming exams with countdown
    badges and completed exams with score outcomes.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()

    qs = Exam.objects.filter(user=user).select_related('subject')

    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in ExamStatus.values:
        qs = qs.filter(status=status_filter)

    exams = list(qs.order_by('exam_date'))

    upcoming_exams = []
    completed_exams = []

    for ex in exams:
        days_left = (ex.exam_date - today).days
        is_overdue = bool(days_left < 0 and ex.status == ExamStatus.UPCOMING)

        data = {
            'exam': ex,
            'days_left': days_left,
            'is_overdue': is_overdue,
            'percentage': ex.percentage_score,
        }

        if ex.status == ExamStatus.COMPLETED or (days_left < 0 and ex.score_achieved is not None):
            completed_exams.append(data)
        else:
            upcoming_exams.append(data)

    context = {
        'page_title': 'Exams & Assessments',
        'active_nav': 'study',
        'upcoming_exams': upcoming_exams,
        'completed_exams': completed_exams,
        'today': today,
        'status_filter': status_filter,
        'statuses': ExamStatus.choices,
    }
    return render(request, 'study/exams.html', context)


@login_required
def exam_create_view(request):
    """
    Schedule a new examination or test.
    """
    if request.method == 'POST':
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.user = request.user
            exam.save()
            messages.success(request, f"Exam '{exam.exam_name}' scheduled for {exam.exam_date}.")
            return redirect('study:exams')
    else:
        initial = {'exam_date': timezone.now().date() + timedelta(days=14)}
        subj_id = request.GET.get('subject', '').strip()
        if subj_id and subj_id.isdigit():
            initial['subject'] = int(subj_id)
        form = ExamForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Schedule Exam',
        'active_nav': 'study',
        'form': form,
    }
    return render(request, 'study/exam_form.html', context)


@login_required
def exam_update_view(request, pk):
    """
    Edit examination details or record obtained marks.
    """
    exam = get_object_or_404(Exam, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam, user=request.user)
        if form.is_valid():
            updated = form.save()
            messages.success(request, f"Exam '{updated.exam_name}' updated.")
            return redirect('study:exams')
    else:
        form = ExamForm(instance=exam, user=request.user)

    context = {
        'page_title': f"Edit Exam — {exam.exam_name}",
        'active_nav': 'study',
        'form': form,
        'exam': exam,
    }
    return render(request, 'study/exam_form.html', context)


@login_required
def exam_delete_view(request, pk):
    """
    Delete an exam with confirmation.
    """
    exam = get_object_or_404(Exam, pk=pk, user=request.user)

    if request.method == 'POST':
        name = exam.exam_name
        exam.delete()
        messages.success(request, f"Exam '{name}' removed.")
        return redirect('study:exams')

    context = {
        'page_title': f"Delete Exam — {exam.exam_name}",
        'active_nav': 'study',
        'exam': exam,
    }
    return render(request, 'study/exam_confirm_delete.html', context)


# ==============================================================================
# 9. STUDY ANALYTICS VIEW
# ==============================================================================

@login_required
def study_analytics_view(request):
    """
    Study analytics: daily study distribution (past 14 days), subject time share,
    syllabus completion rates, consistency score, and planned vs. actual study.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()

    # 1. Past 14 Days Daily Study Duration
    past_14_days = []
    total_14_mins = 0
    days_with_study = 0

    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        mins = StudySession.objects.filter(
            user=user,
            session_date=d,
            duration_minutes__isnull=False
        ).aggregate(total=Sum('duration_minutes'))['total'] or 0

        total_14_mins += mins
        if mins > 0:
            days_with_study += 1

        past_14_days.append({
            'date': d,
            'day_name': d.strftime('%d %b'),
            'minutes': mins,
            'hours': round(mins / 60, 1),
            'formatted': format_duration(mins),
        })

    max_day_mins = max([d['minutes'] for d in past_14_days] + [60])
    for d in past_14_days:
        d['height_pct'] = round((d['minutes'] / max_day_mins) * 100) if max_day_mins > 0 else 0

    consistency_pct = round((days_with_study / 14) * 100)
    avg_daily_minutes = round(total_14_mins / 14)

    # 2. Subject-wise Time Breakdown
    subject_sessions = StudySession.objects.filter(
        user=user,
        duration_minutes__isnull=False
    ).values('subject__name', 'subject__color').annotate(
        total_minutes=Sum('duration_minutes')
    ).order_by('-total_minutes')

    all_study_minutes = sum(s['total_minutes'] for s in subject_sessions) or 1
    subject_time_distribution = []
    for s in subject_sessions:
        pct = round((s['total_minutes'] / all_study_minutes) * 100, 1)
        subject_time_distribution.append({
            'name': s['subject__name'],
            'color': s['subject__color'],
            'minutes': s['total_minutes'],
            'formatted': format_duration(s['total_minutes']),
            'percentage': pct,
        })

    # 3. Subject-wise Syllabus Progress
    subjects = Subject.objects.filter(user=user).prefetch_related('topics')
    syllabus_comparison = []
    for s in subjects:
        t_count = s.topics.count()
        c_count = s.topics.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()
        pct = round((c_count / t_count) * 100) if t_count > 0 else 0
        syllabus_comparison.append({
            'subject': s,
            'total_topics': t_count,
            'completed_topics': c_count,
            'pct': pct,
        })
    syllabus_comparison.sort(key=lambda x: x['pct'], reverse=True)

    # 4. Planned vs Actual Study Time (Past 30 days)
    start_30 = today - timedelta(days=30)
    planned_minutes = StudyPlan.objects.filter(
        user=user,
        planned_date__gte=start_30,
        planned_date__lte=today
    ).aggregate(total=Sum('estimated_minutes'))['total'] or 0

    actual_minutes = StudySession.objects.filter(
        user=user,
        session_date__gte=start_30,
        session_date__lte=today,
        duration_minutes__isnull=False
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0

    plan_adherence_pct = round((actual_minutes / planned_minutes) * 100) if planned_minutes > 0 else 0

    context = {
        'page_title': 'Study Analytics',
        'active_nav': 'study',
        'today': today,

        # Metrics
        'total_14_str': format_duration(total_14_mins),
        'avg_daily_str': format_duration(avg_daily_minutes),
        'consistency_pct': consistency_pct,
        'days_with_study': days_with_study,

        # Visualizations
        'past_14_days': past_14_days,
        'subject_time_distribution': subject_time_distribution,
        'syllabus_comparison': syllabus_comparison,
        'planned_duration_str': format_duration(planned_minutes),
        'actual_duration_str': format_duration(actual_minutes),
        'plan_adherence_pct': plan_adherence_pct,
    }
    return render(request, 'study/analytics.html', context)
