"""
Custom middleware to handle authentication redirects for admin vs SRS
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings


class AdminAuthMiddleware:
    """
    Middleware to ensure admin authentication uses /admin/login/
    while SRS uses /srs/login/
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if this is a redirect to the default login URL from admin
        if (hasattr(response, 'status_code') and 
            response.status_code == 302 and 
            hasattr(response, 'url')):
            
            # If redirecting to /accounts/login/ and the original request was for admin
            if ('/accounts/login/' in response.url and 
                request.path.startswith('/admin/')):
                
                # Extract the 'next' parameter
                next_param = ''
                if '?next=' in response.url:
                    next_param = response.url.split('?next=')[1]
                    next_param = f'?next={next_param}'
                
                # Redirect to admin login instead
                admin_login_url = reverse('admin:login') + next_param
                return redirect(admin_login_url)
        
        return response