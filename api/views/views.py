# api/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from ..forms import RegistrationForm, LoginForm
from ..models import UmUserInformation
from django.contrib.auth.hashers import check_password

# 自定义登录装饰器
def user_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, '请先登录。')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '注册成功，请登录。')
            return redirect('login')
        else:
            messages.error(request, '注册失败，请检查表单。')
    else:
        form = RegistrationForm()
    return render(request, 'api/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user_email = form.cleaned_data['user_email']
            password = form.cleaned_data['password']
            try:
                user = UmUserInformation.objects.get(user_email=user_email)
                if check_password(password, user.user_password):
                    # 设置会话
                    request.session['user_id'] = user.user_id
                    request.session['user_name'] = user.user_name
                    messages.success(request, '登录成功！')
                    return redirect('home')
                else:
                    messages.error(request, '邮箱或密码错误。')
            except UmUserInformation.DoesNotExist:
                messages.error(request, '邮箱或密码错误。')
    else:
        form = LoginForm()
    return render(request, 'api/login.html', {'form': form})

def logout_view(request):
    request.session.flush()
    messages.info(request, '已登出。')
    return redirect('login')

@user_login_required
def home_view(request):
    user_name = request.session.get('user_name')
    return render(request, 'api/home.html', {'user_name': user_name})
