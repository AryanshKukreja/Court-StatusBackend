from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import JsonResponse
from . import views

def api_info(request):
    """Root endpoint providing API information"""
    return JsonResponse({
        'message': 'IITB Sports Facility API',
        'version': '1.0',
        'status': 'active',
        'endpoints': {
            'admin': '/admin/',
            'api_root': '/api/',
            'court_status': '/api/court-status/',
            'update_booking': '/api/update-booking/',
            'sports_list': '/api/sports/',
            'time_slots': '/api/time-slots/',
            'debug': '/api/debug/',
            'create_sample_data': '/api/create-sample-data/',
        }
    })

# Create router for viewsets
router = DefaultRouter()
router.register(r'sports', views.SportViewSet, basename='sport')
router.register(r'time-slots', views.TimeSlotViewSet, basename='timeslot')

urlpatterns = [
    # Root path
    path('', api_info, name='api-info'),
    
    # Include router URLs (this handles /api/sports/ and /api/time-slots/)
    path('api/', include(router.urls)),
    
    # Custom API endpoints
    path('api/court-status/', views.court_status_api, name='court-status'),
    path('api/update-booking/', views.update_booking_api, name='update-booking'),
    
    # Debug/utility routes
    path('api/debug/', views.debug_data_api, name='debug-data'),
    path('api/create-sample-data/', views.create_sample_data, name='create-sample-data'),
]
