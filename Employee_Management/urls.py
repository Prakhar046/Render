"""Employee_Management URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Admin_panel import views as admin_views  # Import from Admin_panel
from Manager import views as manager_views   # Import from Manager
from Employee import views

urlpatterns = [
    # path("admin/", admin.site.urls),
    path('admin/', admin_views.admin_login, name='custom_admin_login'),  # Corrected
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/logout/', admin_views.admin_logout, name='admin_logout'),
    path('manager/login/', manager_views.manager_login, name='manager_login'),
    path('manager/register/', manager_views.manager_register, name='manager_register'),
    path('manager/dashboard/', manager_views.manager_dashboard, name='manager_dashboard'),
    path('manager/logout/', manager_views.manager_logout, name='manager_logout'),
    path("employee/", include('Employee.urls')),
    path("manager/", include('Manager.urls')),
    path("admin/", include('Admin_panel.urls')),
    path("", views.home),
    
]
