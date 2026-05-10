from .views import get_user_id_by_type

def current_user(request):
    return {
        'consumer_user_id': get_user_id_by_type(request, 'consumer'),
        'business_user_id': get_user_id_by_type(request, 'business'),
        'manager_user_id': get_user_id_by_type(request, 'manager'),
    }
