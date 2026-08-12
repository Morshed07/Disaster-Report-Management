from django.urls import path, include

urlpatterns = [

    path('reports/', include('apps.reports.urls')),
    path('messages/', include('apps.messages.urls')),
    path('subsidies/', include('apps.subsidies.urls')),
    path('help-requests/', include('apps.helpRequest.urls')),
    path('reviews/', include('apps.reviews.urls')),
    path('webhooks/', include('apps.reports.webhook_urls')),
]