from django.urls import path, include

urlpatterns = [

    path('', include('apps.reports.urls')),
    path('', include('apps.messages.urls')),

]