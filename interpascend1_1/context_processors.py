from django.conf import settings

def ga_settings(request):
    """Make Google Analytics ID available to all templates."""
    return {
        'GA_ID': getattr(settings, 'GA_ID', None)
    }