"""
URL configuration for the ATMosphere project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    # ATM Social Map REST API — all endpoints under /api/atms/
    path('api/atms/', include('apps.atms.urls', namespace='atms')),

    # Page views
    path('', include('apps.home.urls')),
    path('', include('apps.login.urls')),
    path('', include('apps.register.urls')),
    path('', include('apps.profile.urls')),
    path('', include('apps.settings.urls')),
]
