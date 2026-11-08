"""
URL configuration for LifeOS project.

The `urlpatterns` list routes URLs to views.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.productivity.urls', namespace='productivity')),
    path('', include('apps.planning.urls', namespace='planning')),
    path('', include('apps.study.urls', namespace='study')),
    path('', include('apps.personal.urls', namespace='personal')),
    path('', include('apps.finance.urls', namespace='finance')),
    path('analytics/', include('apps.analytics.urls', namespace='analytics')),
    path('', include('apps.core.urls', namespace='core')),
]

# Custom Production Error Handlers
handler400 = 'apps.core.views.bad_request_view'
handler403 = 'apps.core.views.permission_denied_view'
handler404 = 'apps.core.views.page_not_found_view'
handler500 = 'apps.core.views.server_error_view'

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
