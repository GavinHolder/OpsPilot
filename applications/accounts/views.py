from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse
from .forms import (
    UserRegistrationForm, UserProfileForm, UserForm,
    CustomAuthenticationForm, CompanyForm, DepartmentForm
)
from .models import UserProfile, Company, Department, UserLoginLog


def user_login(request):
    """Handle user login with logging"""
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)

                # Log the login activity
                UserLoginLog.objects.create(
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR', None),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    device_type=get_device_type(request)
                )

                messages.success(request, f"Welcome back, {user.first_name}!")
                # Redirect to dashboard or previous page
                next_url = request.GET.get('next', 'dashboard:index')
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('accounts:login')


def register(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}! Complete your profile.")
            return redirect('accounts:edit_profile')
        else:
            messages.error(request, "Error creating account. Please check the form.")
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    """Display user profile"""
    user = request.user
    return render(request, 'accounts/profile.html', {'user': user})


@login_required
@transaction.atomic
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile was successfully updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)

    return render(request, 'accounts/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def user_list(request):
    """List all users (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard:index')

    search_query = request.GET.get('search', '')
    if search_query:
        users = User.objects.filter(
            username__icontains=search_query
        ) | User.objects.filter(
            first_name__icontains=search_query
        ) | User.objects.filter(
            last_name__icontains=search_query
        ) | User.objects.filter(
            email__icontains=search_query
        )
    else:
        users = User.objects.all()

    users = users.order_by('username')

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/user_table.html', {'users': users})

    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_detail(request, user_id):
    """View user details (admin or self only)"""
    user_obj = get_object_or_404(User, id=user_id)

    # Only allow admins or the user themselves to view profile
    if user_obj != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this profile.")
        return redirect('dashboard:index')

    return render(request, 'accounts/user_detail.html', {'user_obj': user_obj})


@login_required
def user_activity(request, user_id):
    """Get user activity for HTMX partial load"""
    user_obj = get_object_or_404(User, id=user_id)

    # Only allow admins or the user themselves to view activity
    if user_obj != request.user and not request.user.is_staff:
        return HttpResponse("Permission denied", status=403)

    # Get recent login activity
    login_logs = UserLoginLog.objects.filter(user=user_obj).order_by('-login_time')[:10]

    return render(request, 'accounts/partials/user_activity.html', {
        'user_obj': user_obj,
        'login_logs': login_logs
    })


@login_required
def toggle_user_status(request, user_id):
    """Toggle user active status (admin only)"""
    if not request.user.is_staff:
        return HttpResponse("Permission denied", status=403)

    user_obj = get_object_or_404(User, id=user_id)

    # Don't allow deactivating yourself
    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('accounts:user_list')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    status_message = "activated" if user_obj.is_active else "deactivated"
    messages.success(request, f"User {user_obj.username} has been {status_message}.")

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/user_table_row.html', {'user_obj': user_obj})

    return redirect('accounts:user_list')


@login_required
def company_list(request):
    """List all companies (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard:index')

    search_query = request.GET.get('search', '')
    if search_query:
        companies = Company.objects.filter(name__icontains=search_query)
    else:
        companies = Company.objects.all()

    companies = companies.order_by('name')

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/company_table.html', {'companies': companies})

    return render(request, 'accounts/company_list.html', {'companies': companies})


@login_required
def company_create(request):
    """Create a new company (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Company created successfully!")
            return redirect('accounts:company_list')
    else:
        form = CompanyForm()

    return render(request, 'accounts/company_form.html', {'form': form, 'title': 'Create Company'})


@login_required
def company_edit(request, company_id):
    """Edit company details (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard:index')

    company = get_object_or_404(Company, id=company_id)

    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company updated successfully!")
            return redirect('accounts:company_list')
    else:
        form = CompanyForm(instance=company)

    return render(request, 'accounts/company_form.html', {
        'form': form,
        'title': f'Edit Company: {company.name}'
    })


@login_required
def company_detail_partial(request, company_id):
    """Get company details for modal (HTMX)"""
    if not request.user.is_staff:
        return HttpResponse("Permission denied", status=403)

    company = get_object_or_404(Company, id=company_id)
    return render(request, 'accounts/partials/company_detail_modal.html', {'company': company})


@login_required
def toggle_company_status(request, company_id):
    """Toggle company active status (admin only)"""
    if not request.user.is_staff:
        return HttpResponse("Permission denied", status=403)

    company = get_object_or_404(Company, id=company_id)
    company.active = not company.active
    company.save()

    status_message = "activated" if company.active else "deactivated"
    messages.success(request, f"Company {company.name} has been {status_message}.")

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/company_table_row.html', {'company': company})

    return redirect('accounts:company_list')


@login_required
def department_list(request):
    """List all departments (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard:index')

    search_query = request.GET.get('search', '')
    if search_query:
        departments = Department.objects.filter(name__icontains=search_query)
    else:
        departments = Department.objects.all()

    departments = departments.order_by('company', 'name')

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/department_table.html', {'departments': departments})

    return render(request, 'accounts/department_list.html', {'departments': departments})


@login_required
def department_create(request):
    """Create a new department (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created successfully!")
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm()

    return render(request, 'accounts/department_form.html', {'form': form, 'title': 'Create Department'})


@login_required
def department_edit(request, department_id):
    """Edit department details (admin only)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard:index')

    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm(instance=department)

    return render(request, 'accounts/department_form.html', {
        'form': form,
        'title': f'Edit Department: {department.name}'
    })


@login_required
def department_detail_partial(request, department_id):
    """Get department details for modal (HTMX)"""
    if not request.user.is_staff:
        return HttpResponse("Permission denied", status=403)

    department = get_object_or_404(Department, id=department_id)
    return render(request, 'accounts/partials/department_detail_modal.html', {'department': department})


@login_required
def toggle_department_status(request, department_id):
    """Toggle department active status (admin only)"""
    if not request.user.is_staff:
        return HttpResponse("Permission denied", status=403)

    department = get_object_or_404(Department, id=department_id)
    department.active = not department.active
    department.save()

    status_message = "activated" if department.active else "deactivated"
    messages.success(request, f"Department {department.name} has been {status_message}.")

    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/department_table_row.html', {'department': department})

    return redirect('accounts:department_list')


def get_device_type(request):
    """Helper function to determine device type from user agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'Mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'Tablet'
    else:
        return 'Desktop'