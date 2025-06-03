from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
from calendar import monthrange

from .models import Event, EventCategory, EventAttendee, Calendar, CalendarPermission
from .forms import EventForm, EventCategoryForm, CalendarForm, EventAttendeeForm
from applications.tasks.models import Task
from applications.jobs.models import Job


@login_required
def calendar_dashboard(request):
    """Main calendar dashboard view"""
    today = timezone.now().date()

    # Get user's events for today
    today_events = Event.objects.filter(
        Q(attendees=request.user) | Q(created_by=request.user),
        start_datetime__date=today,
        is_cancelled=False
    ).distinct().order_by('start_datetime')

    # Get upcoming events (next 7 days)
    upcoming_events = Event.objects.filter(
        Q(attendees=request.user) | Q(created_by=request.user),
        start_datetime__date__gt=today,
        start_datetime__date__lte=today + timedelta(days=7),
        is_cancelled=False
    ).distinct().order_by('start_datetime')[:5]

    # Get overdue events (for reminders)
    overdue_events = Event.objects.filter(
        Q(attendees=request.user) | Q(created_by=request.user),
        end_datetime__lt=timezone.now(),
        is_cancelled=False
    ).distinct().count()

    # Get pending invitations
    pending_invitations = EventAttendee.objects.filter(
        user=request.user,
        status='PENDING'
    ).select_related('event')

    # Get user's calendars
    user_calendars = Calendar.objects.filter(
        Q(owner=request.user) | Q(shared_with=request.user),
        is_active=True
    ).distinct()

    context = {
        'today_events': today_events,
        'upcoming_events': upcoming_events,
        'overdue_events': overdue_events,
        'pending_invitations': pending_invitations,
        'user_calendars': user_calendars,
        'today': today,
    }

    return render(request, 'calendar_app/dashboard.html', context)


@login_required
def calendar_view(request):
    """Full calendar view with month/week/day options"""
    view_type = request.GET.get('view', 'month')
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    day = int(request.GET.get('day', timezone.now().day))

    # Get date range based on view type
    if view_type == 'month':
        start_date = datetime(year, month, 1).date()
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day).date()
    elif view_type == 'week':
        current_date = datetime(year, month, day).date()
        start_date = current_date - timedelta(days=current_date.weekday())
        end_date = start_date + timedelta(days=6)
    else:  # day view
        start_date = end_date = datetime(year, month, day).date()

    # Get events for the date range
    events = Event.objects.filter(
        Q(attendees=request.user) | Q(created_by=request.user),
        start_datetime__date__gte=start_date,
        start_datetime__date__lte=end_date,
        is_cancelled=False
    ).distinct().select_related('category', 'created_by').prefetch_related('attendees')

    # Get tasks with deadlines in this range
    tasks_with_deadlines = Task.objects.filter(
        Q(assigned_to=request.user) | Q(created_by=request.user),
        deadline__date__gte=start_date,
        deadline__date__lte=end_date,
        status__in=['PENDING', 'IN_PROGRESS']
    ).select_related('category', 'priority')

    # Get jobs scheduled in this range
    scheduled_jobs = Job.objects.filter(
        Q(assigned_team__members=request.user) | Q(created_by=request.user),
        scheduled_start__date__gte=start_date,
        scheduled_start__date__lte=end_date,
        status__in=['PENDING', 'IN_PROGRESS', 'SCHEDULED']
    ).select_related('job_type', 'priority', 'location')

    context = {
        'events': events,
        'tasks_with_deadlines': tasks_with_deadlines,
        'scheduled_jobs': scheduled_jobs,
        'view_type': view_type,
        'current_date': datetime(year, month, day).date(),
        'start_date': start_date,
        'end_date': end_date,
        'year': year,
        'month': month,
        'day': day,
    }

    return render(request, 'calendar_app/calendar_view.html', context)


@login_required
def event_create(request):
    """Create a new event"""
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            form.save_m2m()

            # Add creator as organizer
            EventAttendee.objects.create(
                event=event,
                user=request.user,
                status='ACCEPTED',
                is_organizer=True
            )

            messages.success(request, 'Event created successfully!')
            return redirect('calendar_app:event_detail', pk=event.pk)
    else:
        form = EventForm(user=request.user)

        # Pre-populate with linked task or job if provided
        task_id = request.GET.get('task_id')
        job_id = request.GET.get('job_id')

        if task_id:
            try:
                task = Task.objects.get(pk=task_id)
                form.initial.update({
                    'title': f"Task: {task.title}",
                    'description': task.description,
                    'start_datetime': task.deadline,
                    'linked_task': task,
                })
            except Task.DoesNotExist:
                pass

        if job_id:
            try:
                job = Job.objects.get(pk=job_id)
                form.initial.update({
                    'title': f"Job: {job.title}",
                    'description': job.description,
                    'start_datetime': job.scheduled_start,
                    'location': str(job.location),
                    'linked_job': job,
                })
            except Job.DoesNotExist:
                pass

    context = {
        'form': form,
        'title': 'Create Event',
    }

    return render(request, 'calendar_app/event_form.html', context)


@login_required
def event_detail(request, pk):
    """View event details"""
    event = get_object_or_404(Event, pk=pk)

    # Check if user has access to this event
    if not (event.created_by == request.user or
            event.attendees.filter(pk=request.user.pk).exists()):
        messages.error(request, 'You do not have permission to view this event.')
        return redirect('calendar_app:calendar_dashboard')

    # Get attendee information
    attendees = EventAttendee.objects.filter(event=event).select_related('user')
    user_attendee = attendees.filter(user=request.user).first()

    context = {
        'event': event,
        'attendees': attendees,
        'user_attendee': user_attendee,
        'can_edit': event.created_by == request.user,
    }

    return render(request, 'calendar_app/event_detail.html', context)


@login_required
def event_edit(request, pk):
    """Edit an existing event"""
    event = get_object_or_404(Event, pk=pk)

    # Check permissions
    if event.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('calendar_app:event_detail', pk=pk)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('calendar_app:event_detail', pk=pk)
    else:
        form = EventForm(instance=event, user=request.user)

    context = {
        'form': form,
        'event': event,
        'title': 'Edit Event',
    }

    return render(request, 'calendar_app/event_form.html', context)


@login_required
@require_http_methods(["POST"])
def event_delete(request, pk):
    """Delete an event"""
    event = get_object_or_404(Event, pk=pk)

    # Check permissions
    if event.created_by != request.user:
        messages.error(request, 'You do not have permission to delete this event.')
        return redirect('calendar_app:event_detail', pk=pk)

    event.delete()
    messages.success(request, 'Event deleted successfully!')
    return redirect('calendar_app:calendar_dashboard')


@login_required
@require_http_methods(["POST"])
def event_rsvp(request, pk):
    """RSVP to an event"""
    event = get_object_or_404(Event, pk=pk)
    status = request.POST.get('status')

    if status not in ['ACCEPTED', 'DECLINED', 'TENTATIVE']:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    attendee, created = EventAttendee.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={'status': status, 'response_date': timezone.now()}
    )

    if not created:
        attendee.status = status
        attendee.response_date = timezone.now()
        attendee.save()

    return JsonResponse({
        'success': True,
        'status': status,
        'message': f'RSVP updated to {status.title()}'
    })


@login_required
def events_api(request):
    """API endpoint for calendar events (for HTMX/JavaScript)"""
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if not start_date or not end_date:
        return JsonResponse({'error': 'Start and end dates required'}, status=400)

    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # Get events
    events = Event.objects.filter(
        Q(attendees=request.user) | Q(created_by=request.user),
        start_datetime__date__gte=start_date,
        start_datetime__date__lte=end_date,
        is_cancelled=False
    ).distinct().select_related('category')

    events_data = []
    for event in events:
        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.start_datetime.isoformat(),
            'end': event.end_datetime.isoformat(),
            'allDay': event.all_day,
            'color': event.category.color,
            'url': event.get_absolute_url(),
            'description': event.description[:100] + '...' if len(event.description) > 100 else event.description,
        })

    return JsonResponse(events_data, safe=False)


@login_required
def calendar_management(request):
    """Manage user calendars"""
    user_calendars = Calendar.objects.filter(
        Q(owner=request.user) | Q(shared_with=request.user)
    ).distinct().select_related('owner', 'company', 'department')

    context = {
        'calendars': user_calendars,
    }

    return render(request, 'calendar_app/calendar_management.html', context)


@login_required
def calendar_create(request):
    """Create a new calendar"""
    if request.method == 'POST':
        form = CalendarForm(request.POST, user=request.user)
        if form.is_valid():
            calendar = form.save(commit=False)
            calendar.owner = request.user
            calendar.save()
            messages.success(request, 'Calendar created successfully!')
            return redirect('calendar_app:calendar_management')
    else:
        form = CalendarForm(user=request.user)

    context = {
        'form': form,
        'title': 'Create Calendar',
    }

    return render(request, 'calendar_app/calendar_form.html', context)


@login_required
def quick_event_create(request):
    """Quick event creation via HTMX"""
    if request.method == 'POST':
        title = request.POST.get('title')
        start_date = request.POST.get('start_date')
        start_time = request.POST.get('start_time', '09:00')

        if title and start_date:
            try:
                start_datetime = datetime.strptime(f"{start_date} {start_time}", '%Y-%m-%d %H:%M')
                end_datetime = start_datetime + timedelta(hours=1)

                # Get or create default category
                category, _ = EventCategory.objects.get_or_create(
                    name='General',
                    defaults={'event_type': 'MEETING', 'color': '#3498db'}
                )

                event = Event.objects.create(
                    title=title,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    category=category,
                    created_by=request.user
                )

                # Add creator as attendee
                EventAttendee.objects.create(
                    event=event,
                    user=request.user,
                    status='ACCEPTED',
                    is_organizer=True
                )

                return JsonResponse({
                    'success': True,
                    'event_id': event.id,
                    'message': 'Event created successfully!'
                })

            except ValueError:
                return JsonResponse({'error': 'Invalid date/time format'}, status=400)

        return JsonResponse({'error': 'Title and date are required'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)