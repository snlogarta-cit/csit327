from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url='login')
def home_view(request):
    """
    Renders the ATM Social Map home page.
    The CSRF token is available via the {{ csrf_token }} template tag,
    which the Leaflet JS uses for authenticated POST requests to the API.
    """
    return render(request, 'home/home.html', {
        'username': request.user.username,
    })
