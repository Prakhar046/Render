from django.urls import path
from Employee import views
from .views import *
urlpatterns = [
    path("form/", views.employee_form, name="employee_form"),  # Employee form page
    path("save/", views.save_employee, name="save_employee"),  # Save employee data
    path("", home),
    path("login/", views.employee_login, name="employee_login"),  # Save employee data
    path("logout/", views.employee_logout, name="employee_logout"),
    path("employee_dashboard/", views.employee_dashboard, name="employee_dashboard"),  # Save employee data
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password/<str:token>/', views.reset_password, name='reset_password'),
    
]
