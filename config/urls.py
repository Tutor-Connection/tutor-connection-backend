from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/accounts/', include('apps.accounts.urls')),
    path('api/tutoring/', include('apps.tutoring.urls')),
    path('api/communication/', include('apps.communication.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/support/', include('apps.support.urls')),
]