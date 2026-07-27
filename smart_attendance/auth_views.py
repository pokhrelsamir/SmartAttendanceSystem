from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('landing_page')   # Landing Page Rule
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password.'})

    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login_page')


# from django.contrib.auth import authenticate, login, logout
# from django.shortcuts import render, redirect

# def login_view(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             login(request, user)

#             if user.groups.filter(name='Admin').exists() or user.is_superuser:
#                 return redirect('register_page')
#             elif user.groups.filter(name='Teacher').exists():
#                 return redirect('attendance_live_page')
#             else:
#                 return redirect('landing_page')
#         else:
#             return render(request, 'login.html', {'error': 'Invalid username or password.'})

#     return render(request, 'login.html')

# def logout_view(request):
#     logout(request)
#     return redirect('login_page')