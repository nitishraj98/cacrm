from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if 'Token is blacklisted' in response.data.get('detail', ''):
            response.data = {
                "error": "Token is blacklisted"
            }
        elif 'Invalid token' in response.data.get('detail', ''):
            response.data = {
                "error": "Token is invalid or expired"
            }
        elif 'Authorization header must start with Bearer ' in response.data.get('detail', ''):
            response.data = {
                "error": "Authorization header must start with Bearer "
            }
        else:
            response.data = {
                "error": response.data.get('detail', 'An unexpected error occurred')
            }
        
        response.status_code = response.status_code  
    return response
