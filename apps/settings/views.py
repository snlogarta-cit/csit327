from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import CalmPasswordChangeForm


@login_required(login_url='login')
def settings_view(request):
    if request.method == 'POST':
        form = CalmPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was updated successfully.')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors in the password change form.')
    else:
        form = CalmPasswordChangeForm(user=request.user)

    return render(request, 'settings/settings.html', {'form': form})
