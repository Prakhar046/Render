from django.shortcuts import render, redirect
from pymongo import MongoClient
from django.http import HttpResponse
from django.contrib import messages
from django.core.mail import send_mail
import datetime, hashlib , uuid
from datetime import datetime, timedelta
import datetime

# MongoDB Connection
# client = MongoClient('mongodb://localhost:27017/')
client = MongoClient('mongodb+srv://Prakhar:Prakhar%40123@cluster0.l2jvk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

db = client['Employee_Management']
employee_collection = db['Employees']
manager_collection = db['Manager']
department_collection = db['Departments']
employee_activity_collection = db['Employee_Activity']
employee_attendance_collection = db['Employee_Attendance']
leave_requests_collection = db['Leave_Request']


def home(request):
    return render(request, "home.html")

def employee_form(request):
    return render(request, "employee_form.html")


def save_employee(request):
    if request.method == "POST":
        employee_id = int(request.POST["employee_id"])
        
        # Check if employee ID already exists in pending or approved employees
        if db['pending_employees'].find_one({"employee_id": employee_id}) or db['Employees'].find_one({"employee_id": employee_id}):
            return render(request, 'employee_form.html', {
                "error_message": "Employee ID already exists. Please use a unique employee ID.",
                "department_name": request.POST.get("department_name", "")
            })
        
        # Ensure passwords match
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        if password != confirm_password:
            return render(request, 'employee_form.html', {
                "error_message": "Passwords do not match!",
                "department_name": request.POST.get("department_name", "")
            })

        # Hash the password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        
        # Fetch the department name from the department collection using department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            #messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "employee_form.html",{
                "error_message": f"Department ID {department_id} not found.",      
            })
        
        department_name = department["department_name"]  # Fetch the department name

        
        
        # Employee data
        employee_data = {
            "employee_id": employee_id,
            "first_name": request.POST["first_name"],
            "last_name": request.POST["last_name"],
            "password": hashed_password,
            "email": request.POST["email"],
            "phone": request.POST["phone"],
            "date_of_birth": datetime.datetime.strptime(request.POST["date_of_birth"], "%Y-%m-%d"),
            "date_of_joining": datetime.datetime.strptime(request.POST["date_of_joining"], "%Y-%m-%d"),
            # "department_id": int(request.POST["department_id"]),
            "department_id": department_id,
            "department_name": department_name,  # Automatically added
            "role_id": int(request.POST["role_id"]),
            "salary": float(request.POST["salary"]),
            "status": request.POST["status"],  # Status set to Pending
            "address": request.POST["address"],
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
        }

        # Save to pending_employees
        db['pending_employees'].insert_one(employee_data)

        # After successful registration, show a success message on the form
        return render(request, 'employee_form.html', {
            "success_message": "Registration submitted. Waiting for admin approval!",
            "department_name": department_name,
        })
    else:
        return render(request, 'employee_form.html', {
            "department_name": ""  # Make sure to pass this value for the GET request as well
        })
        #return HttpResponse("Invalid request method.")




def employee_login(request):
    if request.method == "POST":
        employee_id = int(request.POST["employee_id"])
        password = request.POST["password"]

        # Hash the password for comparison
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Find the employee in Employees collection
        employee = employee_collection.find_one({
            "employee_id": employee_id,
            "password": hashed_password,
            "registration": "Approved"
        })

        
        if employee:
            # Set session for the logged-in employee
            request.session['employee_id'] = employee['employee_id']  # Use employee_id to identify the employee
            request.session.set_expiry(300)  # Set session expiry for 5 minutes
            
            email = employee.get("email")
            # Store login activity in database
            activity_data = {
                "employee_id": employee_id,
                "email": email, 
                "action": "login",
                "timestamp": datetime.datetime.now()
            }
            employee_activity_collection.insert_one(activity_data)
            messages.success(request, "Login Successful!")
            return redirect('employee_dashboard')  # Redirect to employee dashboard
        else:
            messages.error(request, "Invalid credentials or account not approved!")
            return render(request, "employee_login.html")
    
    # Render the login page for GET requests
    return render(request, "employee_login.html")




#@login_required
def employee_dashboard(request):
    employee_id = request.session.get('employee_id')

    if not employee_id:
        # Retrieve last known employee_id from cookies
        last_employee_id = request.COOKIES.get('last_employee_id')

        if last_employee_id:
            employee_activity_collection.insert_one({
                "employee_id": int(last_employee_id),
                "action": "logout",
                "timestamp": datetime.datetime.now()
            })
        return redirect('employee_login')  # If no employee_id in session, redirect to login page

    # Find the employee's current details
    employee = employee_collection.find_one({"employee_id": employee_id})

    if not employee:
        messages.error(request, "Employee not found!")
        return redirect('employee_login')

    
     # Get current attendance record for the employee (if any)
    attendance = employee_attendance_collection.find_one({"employee_id": employee_id, "end_time": None})

     # Retrieve existing leave requests for this employee
    leave_requests = leave_requests_collection.find({"employee_id": employee_id})

    
    if request.method == "POST":
        
         # Handle Leave Application
        if 'apply_leave' in request.POST:
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")
            reason = request.POST.get("reason")

            department_id = employee.get("department_id")
            manager = manager_collection.find_one({"department_id": department_id})

            if not manager:
                messages.error(request, "No manager found for your department!")
                return redirect('employee_dashboard')

            manager_id = manager.get("manager_id")

            leave_request = {
                "employee_id": employee_id,
                "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
                "department_id": department_id,
                "manager_id": manager_id,
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
                "status": "Pending",
                "applied_at": datetime.datetime.now(),
                "updated_at": datetime.datetime.now(),
            }

            leave_requests_collection.insert_one(leave_request)
            messages.success(request, "Leave request submitted successfully!")
        
        if 'start_stop_button' in request.POST:
            if not attendance:  # If no start time, start a new attendance record
                start_time = datetime.datetime.now()
                employee_attendance_collection.insert_one({
                    "employee_id": employee_id,
                    "employee_name": f"{employee.get('first_name')} {employee.get('last_name')}",
                    "start_time": start_time,
                    "end_time": None,
                    "attendance_type": None
                })
                messages.success(request, "Attendance started!")
            else:  # If there's an existing start time, stop the attendance
                end_time = datetime.datetime.now()
                time_diff = end_time - attendance['start_time']
                
                # Calculate attendance type based on the time difference
                attendance_type = "half_day" if time_diff < timedelta(hours=3.5) else "full_day"
                
                # Update the attendance record with end_time and attendance_type
                employee_attendance_collection.update_one(
                    {"_id": attendance['_id']},
                    {"$set": {
                        "end_time": end_time,
                        "attendance_type": attendance_type
                    }}
                )
                messages.success(request, f"Attendance stopped! Marked as {attendance_type}.")
        
        
        # Update all employee fields
        updated_first_name = request.POST.get("first_name", employee.get("first_name"))
        updated_last_name = request.POST.get("last_name", employee.get("last_name"))
        updated_email = request.POST.get("email", employee.get("email"))
        updated_phone = request.POST.get("phone", employee.get("phone"))
        updated_date_of_birth = request.POST.get("date_of_birth", employee.get("date_of_birth"))
        updated_date_of_joining = request.POST.get("date_of_joining", employee.get("date_of_joining"))
        updated_department_id = int(request.POST.get("department_id", employee.get("department_id")))
        #updated_department_name = request.POST.get("department_name", employee.get("department_name"))
        updated_role_id = request.POST.get("role_id", employee.get("role_id"))
        updated_salary = float(request.POST.get("salary", employee.get("salary")))
        updated_status = request.POST.get("status", employee.get("status"))
        updated_address = request.POST.get("address", employee.get("address"))
        
         # If the department ID has changed, fetch the new department name from the manager table
        if updated_department_id != employee.get("department_id"):
            department = department_collection.find_one({"department_id": updated_department_id})
            updated_department_name = department.get("department_name") if department else "Unknown"
        else:
            updated_department_name = employee.get("department_name")
        
        
        # Update employee details in the database
        employee_collection.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "first_name": updated_first_name,
                "last_name": updated_last_name,
                "email": updated_email,
                "phone": updated_phone,
                "date_of_birth": updated_date_of_birth,
                "date_of_joining": updated_date_of_joining,
                "department_id": updated_department_id,
                "department_name": updated_department_name,
                "role_id": updated_role_id,
                "salary": updated_salary,
                "status": updated_status,
                "address": updated_address,
                "updated_at": datetime.datetime.now(),
            }}
        )

        messages.success(request, "Your details have been updated successfully!")
        # Render the employee dashboard with current details
        return redirect('employee_dashboard')
    
     # Store last logged-in employee_id in cookies to track session expiry
    response = render(request, "employee_dashboard.html", {"employee": employee, "attendance": attendance, "leave_requests": leave_requests})
    response.set_cookie('last_employee_id', employee_id, max_age=300)  # 5 minutes

    return response
       
    # # Render the employee dashboard with current details
    # return render(request, "employee_dashboard.html", {"employee": employee})



# def employee_logout(request):
#     try:
#         del request.session['employee_id']  # Clear the session data
#     except KeyError:
#         pass
#     return redirect('employee_login')  # Redirect to login page after logout



def employee_logout(request):
    employee_id = request.session.get('employee_id')

    if employee_id:
         # Find the employee's email from the employee collection
        employee = employee_collection.find_one({"employee_id": employee_id})
        email = employee.get("email")

        # Store logout activity in the database
        activity_data = {
            "employee_id": employee_id,
            "email": email,
            "action": "logout",
            "timestamp": datetime.datetime.now()
        }
        employee_activity_collection.insert_one(activity_data)

        # Clear the session
        request.session.flush()

    return redirect('employee_login')








# Password reset request view
def forgot_password(request):
    if request.method == "POST":
        email = request.POST["email"]
        employee = employee_collection.find_one({"email": email})
        
        if employee:
            # Generate a unique token
            token = str(uuid.uuid4())
            # Save the token in the employee document (you can store it in the database with an expiration time)
            employee_collection.update_one(
                {"email": email},
                {"$set": {
                    "reset_token": token,
                    "reset_token_created_at": datetime.datetime.now(),  # Store the current timestamp
                    }
                 }
            )
            
            # Generate reset link
            reset_link = request.build_absolute_uri(f"/employee/reset_password/{token}/")
            
            # Send email
            send_mail(
                'Password Reset Request',
                f'Click the link below to reset your password: {reset_link}',
                'prakhar9522@gmail.com',
                [email],
                fail_silently=False,
            )
            return render(request, "forgot_password.html", {
                "success_message": "A password reset link has been sent to your email."
            })
            return HttpResponse("A password reset link has been sent to your email.")
        else:
            return render(request, "forgot_password.html", {
                "error_message": "Email not found."
            })
            return HttpResponse("Email not found.")
    
    return render(request, "forgot_password.html")








def reset_password(request, token):
    if request.method == "POST":
        new_password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        
        if new_password != confirm_password:
            return render(request, "reset_password.html", {
                "error_message": "Passwords do not match!",
            })
            return HttpResponse("Passwords do not match.")
        
        # Hash the new password
        hashed_password = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
        
        
        # Find the user by the reset token
        employee = employee_collection.find_one({"reset_token": token})
        if not employee:
            return render(request, "reset_password.html", {
                "error_message": "Invalid or expired reset token.",
            })

        # Check if the token has expired
        token_created_at = employee.get("reset_token_created_at")
        if not token_created_at or (datetime.datetime.now() - token_created_at) > timedelta(minutes=30):
            return render(request, "reset_password.html", {
                "error_message": "Reset token has expired.",
            })

        

        # Update the password in the database
        employee_collection.update_one(
            {"reset_token": token},
            {"$set": {
                "password": hashed_password,
                "updated_at": datetime.datetime.now(),
                },
                "$unset": {
                    "reset_token": "",  # Remove the token
                    "reset_token_created_at": "",  # Remove the timestamp
                }
            }
        )

        messages.success(request, "Password reset successfully! You can now log in with your new password.")
        return redirect("employee_login")

    return render(request, "reset_password.html")