from datetime import datetime, timedelta
from django.utils.timezone import now
from django.conf import settings
from django.contrib.auth import logout

class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request here if needed

        # Get the response from the next middleware or view
        response = self.get_response(request)

        # Process the response here if needed

        return response

    def process_request(self, request):
        if not request.user.is_authenticated:
            return  

        # Get the last activity time from the session
        last_activity = request.session.get('last_activity')

        # Convert the last_activity string back to datetime
        if last_activity:
            last_activity = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S.%f')

            # Check if the time exceeded the limit
            if now() - last_activity > timedelta(minutes=3):
                # Log out the user
                logout(request)
                return

        # Update last_activity time
        request.session['last_activity'] = now().strftime('%Y-%m-%d %H:%M:%S.%f')