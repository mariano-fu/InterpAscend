"""
Favorites-related views for the terminology app.
Handles the dedicated favorites page and related functionality.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


def favorites_page(request):
    """
    Dedicated favorites page that opens in a new tab.
    Provides enhanced favorites management interface.
    """
    context = {
        'page_title': 'My Favorites - InterpAscend',
        'is_favorites_page': True,
    }
    return render(request, 'terminology/favorites_page.html', context)


@require_http_methods(["GET"])
def favorites_api(request):
    """
    API endpoint to get favorites data for the standalone page.
    Returns JSON data that can be consumed by JavaScript.
    """
    # Since favorites are stored in localStorage, we don't need server-side data
    # This endpoint can be used for future server-side favorites if needed
    return JsonResponse({
        'status': 'success',
        'message': 'Favorites are managed client-side via localStorage',
        'storage_key': 'ia_favorites_v1'
    })


@csrf_exempt
@require_http_methods(["POST"])
def favorites_export(request):
    """
    Export favorites data in various formats.
    Accepts JSON data from client and returns formatted export.
    """
    try:
        data = json.loads(request.body)
        favorites = data.get('favorites', [])
        export_format = data.get('format', 'json')
        
        if export_format == 'json':
            response = JsonResponse({
                'status': 'success',
                'data': favorites,
                'exported_at': data.get('timestamp'),
                'total_count': len(favorites)
            })
            response['Content-Disposition'] = 'attachment; filename="interpascend_favorites.json"'
            return response
            
        elif export_format == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="interpascend_favorites.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Source Term', 'Target Term', 'Source Language', 'Target Language', 'Domain', 'Added Date'])
            
            for fav in favorites:
                writer.writerow([
                    fav.get('src', ''),
                    fav.get('tgt', ''),
                    fav.get('srcLang', ''),
                    fav.get('tgtLang', ''),
                    fav.get('domain', ''),
                    fav.get('timestamp', '')
                ])
            
            return response
            
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Unsupported export format'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)