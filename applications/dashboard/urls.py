from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='index'),
    path('dashboard/notifications/', views.notifications_panel, name='notifications_panel'),
    path('dashboard/tasks-today/', views.tasks_today_panel, name='tasks_today_panel'),
    path('dashboard/insights/', views.insights_panel, name='insights_panel'),
    path('dashboard/open-jobs/', views.open_jobs_panel, name='open_jobs_panel'),
    path('dashboard/approvals/', views.approvals_panel, name='approvals_panel'),
    path('dashboard/messages/', views.messages_panel, name='messages_panel'),
    path('dashboard/stock-warnings/', views.stock_warnings_panel, name='stock_warnings_panel'),
    path('dashboard/events/', views.events_panel, name='events_panel'),
]