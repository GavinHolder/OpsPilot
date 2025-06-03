from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from applications.accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('applications.dashboard.urls')),
    path('tasks/', include('applications.tasks.urls')),
    path('jobs/', include('applications.jobs.urls')),
    path('inventory/', include('applications.inventory.urls')),
    path('calendar/', include('applications.calendar_app.urls')),
    path('communication/', include('applications.communication.urls')),
    path('accounts/', include('applications.accounts.urls')),

    # Login
    path('login/', account_views.user_login, name='login'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
