from django.urls import path
from Manager import views

urlpatterns = [
    path("dashboard/", views.manager_dashboard, name="manager_dashboard"),
    path("manager_add/", views.manager_add_employee, name="add_employee"),
    path("edit/<int:employee_id>/", views.edit_employee, name="edit_employee"),
    path("delete/<int:employee_id>/", views.delete_employee, name="delete_employee"),
    
    # path('register/', views.manager_register, name='manager_register'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password/<str:token>/', views.reset_password, name='reset_password'),
    path('edit_manager/', views.manager_edit, name='manager_edit'),

]
