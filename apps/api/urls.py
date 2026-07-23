from django.urls import path, include

urlpatterns = [

    path('reports/', include('apps.reports.urls')),
    path('messages/', include('apps.messages.urls')),
    path('subsidies/', include('apps.subsidies.urls')), # Temporarily disabled
]   