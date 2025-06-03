# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


@login_required
def dashboard(request):
    """Main dashboard view showing all panels"""
    context = {
        'page_title': 'OpsPilot Dashboard',
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def notifications_panel(request):
    """HTMX panel for notifications"""
    # Placeholder for notifications data
    notifications = [
        {'id': 1, 'message': 'Tower 3 maintenance overdue', 'urgency': 'high', 'created_at': '2 hours ago'},
        {'id': 2, 'message': 'FNO team completed Job #124', 'urgency': 'medium', 'created_at': '4 hours ago'},
        {'id': 3, 'message': 'New stock request from Tower Team', 'urgency': 'low', 'created_at': '1 day ago'},
    ]

    context = {
        'notifications': notifications
    }
    return render(request, 'dashboard/panels/notifications.html', context)


@login_required
def tasks_today_panel(request):
    """HTMX panel for today's tasks"""
    # Placeholder for tasks data
    tasks = [
        {'id': 1, 'title': 'Call supplier about fiber delivery', 'status': 'pending', 'deadline': 'Today 15:00'},
        {'id': 2, 'title': 'Review Tower 7 maintenance report', 'status': 'in_progress', 'deadline': 'Today 17:00'},
        {'id': 3, 'title': 'Meeting with civil team', 'status': 'completed', 'deadline': 'Today 12:00'},
    ]

    context = {
        'tasks': tasks
    }
    return render(request, 'dashboard/panels/tasks_today.html', context)


@login_required
def insights_panel(request):
    """HTMX panel for AI insights"""
    # Placeholder for insights data
    insights = [
        {'id': 1, 'message': 'Civil team performance improved by 12% this month', 'type': 'performance'},
        {'id': 2, 'message': 'Tower 4 has had 3 similar issues in the past month', 'type': 'pattern'},
        {'id': 3, 'message': 'Stock levels for fiber cables are trending down', 'type': 'warning'},
    ]

    context = {
        'insights': insights
    }
    return render(request, 'dashboard/panels/insights.html', context)


@login_required
def open_jobs_panel(request):
    """HTMX panel for open jobs"""
    # Placeholder for open jobs data
    jobs = [
        {'id': 101, 'title': 'Tower 3 Radio Replacement', 'team': 'Tower Team', 'status': 'in_progress',
         'days_open': 2},
        {'id': 102, 'title': 'Fiber Installation at Kleinmond Mall', 'team': 'FNO Team', 'status': 'scheduled',
         'days_open': 1},
        {'id': 103, 'title': 'Network Outage at Tower 5', 'team': 'Tower Team', 'status': 'pending', 'days_open': 0},
    ]

    context = {
        'jobs': jobs
    }
    return render(request, 'dashboard/panels/open_jobs.html', context)


@login_required
def approvals_panel(request):
    """HTMX panel for pending approvals"""
    # Placeholder for approvals data
    approvals = [
        {'id': 201, 'title': 'Purchase Order: 50m Fiber Cable', 'requester': 'John (FNO Team)', 'amount': 'R 5,200'},
        {'id': 202, 'title': 'Civil Team Overtime Request', 'requester': 'Sarah (Civil Team)', 'amount': '8 hours'},
        {'id': 203, 'title': 'New Radio Equipment Quote', 'requester': 'Michael (Tower Team)', 'amount': 'R 12,350'},
    ]

    context = {
        'approvals': approvals
    }
    return render(request, 'dashboard/panels/approvals.html', context)


@login_required
def messages_panel(request):
    """HTMX panel for internal messages"""
    # Placeholder for messages data
    messages = [
        {'id': 301, 'sender': 'Tower Team Lead', 'subject': 'Weekly Maintenance Update', 'received': 'Today 09:15'},
        {'id': 302, 'sender': 'FNO Manager', 'subject': 'New Client Installation Query', 'received': 'Yesterday 16:30'},
        {'id': 303, 'sender': 'CEO', 'subject': 'Monthly Performance Review', 'received': '2 days ago'},
    ]

    context = {
        'messages': messages
    }
    return render(request, 'dashboard/panels/messages.html', context)


@login_required
def stock_warnings_panel(request):
    """HTMX panel for stock warnings"""
    # Placeholder for stock warnings data
    warnings = [
        {'id': 401, 'item': 'Fiber Cable (50m)', 'current_stock': 2, 'minimum_level': 5, 'company': 'FNO'},
        {'id': 402, 'item': 'Radio Units (5GHz)', 'current_stock': 1, 'minimum_level': 3, 'company': 'WISP'},
        {'id': 403, 'item': 'Network Switches', 'current_stock': 0, 'minimum_level': 2, 'company': 'WISP'},
    ]

    context = {
        'warnings': warnings
    }
    return render(request, 'dashboard/panels/stock_warnings.html', context)


@login_required
def events_panel(request):
    """HTMX panel for upcoming events"""
    # Placeholder for events data
    events = [
        {'id': 501, 'title': 'Weekly Staff Meeting', 'time': 'Tomorrow 09:00', 'location': 'Main Office'},
        {'id': 502, 'title': 'Tower 7 Maintenance', 'time': 'Tomorrow 13:00', 'location': 'Tower 7 Site'},
        {'id': 503, 'title': 'Supplier Meeting', 'time': 'Thursday 11:00', 'location': 'Virtual (Zoom)'},
    ]

    context = {
        'events': events
    }
    return render(request, 'dashboard/panels/events.html', context)