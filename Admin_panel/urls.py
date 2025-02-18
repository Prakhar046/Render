from django.urls import path
from Admin_panel import views
from .views import *

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
    path("logout/", views.admin_logout, name="admin_logout"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin_add/", views.add_employee_admin, name="add_employee"),
    path("admin_edit/<int:employee_id>/", views.edit_employee, name="edit_employee"),
    path("admin_delete/<int:employee_id>/", views.delete_employee, name="delete_employee"),
    path("add-manager/", views.add_manager, name="add_manager"),
    path("edit-manager/<int:manager_id>/", views.edit_manager, name="edit_manager"),
    path("delete-manager/<int:manager_id>/", views.delete_manager, name="delete_manager"),
    path('employee-leaves/', employee_leaves, name='employee_leaves'),
    #path('download-attendance/', download_attendance_csv, name='download_attendance_csv'),
    path('employee-attendance/', employee_attendance_details, name='employee_attendance_details'),
    path('download-attendance/<int:employee_id>/', download_attendance_csv, name='download_attendance_csv'),
    path('employee-activity/', employee_activity, name='employee_activity'),
    path('download-employee-activity/<int:employee_id>/', views.download_employee_activity_csv, name='download_employee_activity_csv'),

]
