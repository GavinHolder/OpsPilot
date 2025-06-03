from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Company, Department, UserProfile,
    UserSkill, UserSkillAssignment, UserLoginLog
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class UserSkillAssignmentInline(admin.TabularInline):
    model = UserSkillAssignment
    extra = 1


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_department', 'get_role', 'is_staff')
    list_filter = ('profile__role', 'profile__department', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__phone_number')

    def get_department(self, obj):
        return obj.profile.department if obj.profile.department else "-"
    get_department.short_description = 'Department'

    def get_role(self, obj):
        return obj.profile.get_role_display()
    get_role.short_description = 'Role'


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'phone_number', 'is_active')
    list_filter = ('role', 'department', 'is_active')
    search_fields = ('user__username', 'user__email', 'phone_number')
    inlines = (UserSkillAssignmentInline,)


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_type', 'active')
    list_filter = ('company_type', 'active')
    search_fields = ('name', 'description')


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'active')
    list_filter = ('company', 'active')
    search_fields = ('name', 'description')


class UserSkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')


class UserLoginLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'ip_address', 'device_type')
    list_filter = ('login_time', 'device_type')
    search_fields = ('user__username', 'ip_address')
    date_hierarchy = 'login_time'
    readonly_fields = ('user', 'login_time', 'ip_address', 'user_agent', 'device_type')


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Register other models
admin.site.register(Company, CompanyAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserSkill, UserSkillAdmin)
admin.site.register(UserLoginLog, UserLoginLogAdmin)