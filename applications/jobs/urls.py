from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Job List Views
    path('', views.JobListView.as_view(), name='job_list'),
    path('calendar/', views.job_calendar, name='job_calendar'),
    path('board/', views.job_board, name='job_board'),
    path('map/', views.job_map, name='job_map'),

    # Job CRUD
    path('create/', views.JobCreateView.as_view(), name='job_create'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('<int:pk>/edit/', views.JobUpdateView.as_view(), name='job_update'),
    path('<int:pk>/delete/', views.JobDeleteView.as_view(), name='job_delete'),

    # Job Actions
    path('<int:pk>/start/', views.mark_job_started, name='mark_started'),
    path('<int:pk>/complete/', views.mark_job_completed, name='mark_completed'),
    path('<int:pk>/add-note/', views.add_job_note, name='add_note'),
    path('<int:pk>/add-attachment/', views.add_job_attachment, name='add_attachment'),
    path('<int:pk>/add-task/', views.add_job_task, name='add_task'),
    path('<int:pk>/add-civil-worker/', views.add_civil_worker, name='add_civil_worker'),
    path('<int:pk>/add-inventory/', views.add_inventory_usage, name='add_inventory'),

    # Task Actions
    path('task/<int:task_pk>/toggle/', views.toggle_job_task, name='toggle_task'),

    # Civil Worker Assignment Actions
    path('civil-assignment/<int:assignment_pk>/end/', views.end_civil_worker_assignment, name='end_civil_assignment'),

    # Location Management
    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('locations/create/', views.LocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/', views.LocationDetailView.as_view(), name='location_detail'),
    path('locations/<int:pk>/edit/', views.LocationUpdateView.as_view(), name='location_update'),

    # Team Management
    path('teams/', views.TeamListView.as_view(), name='team_list'),
    path('teams/create/', views.TeamCreateView.as_view(), name='team_create'),
    path('teams/<int:pk>/', views.TeamDetailView.as_view(), name='team_detail'),
    path('teams/<int:pk>/edit/', views.TeamUpdateView.as_view(), name='team_update'),

    # Civil Worker Management
    path('civil-workers/', views.CivilWorkerListView.as_view(), name='civil_worker_list'),
    path('civil-workers/create/', views.CivilWorkerCreateView.as_view(), name='civil_worker_create'),
    path('civil-workers/<int:pk>/', views.CivilWorkerDetailView.as_view(), name='civil_worker_detail'),
    path('civil-workers/<int:pk>/edit/', views.CivilWorkerUpdateView.as_view(), name='civil_worker_update'),

    # Job API Endpoints
    path('api/calendar-events/', views.job_calendar_events, name='calendar_events'),
    path('api/<int:pk>/summary/', views.job_detail_api, name='job_detail_api'),
]
