from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import UserRegisterForm


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful.')
            return redirect('accounts:redirect')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def role_redirect_view(request):
    if request.user.is_staff or request.user.role == 'admin':
        return redirect('parking:dashboard')
    return redirect('booking:user_home')
