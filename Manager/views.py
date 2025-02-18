from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from pymongo import MongoClient
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from bson import ObjectId  # Import ObjectId for MongoDB document IDs
from django.contrib.auth.hashers import make_password
import datetime, hashlib, uuid
import random, string



# MongoDB connection (same as admin)
#client = MongoClient('mongodb://localhost:27017/')
client = MongoClient('mongodb+srv://Prakhar:Prakhar%40123@cluster0.l2jvk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client['Employee_Management']
employee_collection = db['Employees']
manager_collection = db['Manager']
department_collection = db['Departments']
leave_requests_collection = db['Leave_Request']
pending_registrations = db['pending_registrations']


def manager_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        
        
        # Hash the entered password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Check if manager is approved
        manager = db['Manager'].find_one({"username": username, "password": hashed_password})
        if manager:
            request.session['manager_username'] = username  # Store session for logged-in manager
            messages.success(request, "Login Successful!")
            return redirect('manager_dashboard')
        else:
            messages.error(request, "Invalid credentials or account not approved!")
            return render(request, 'manager_login.html')

    return render(request, 'manager_login.html')






def manager_register(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        email = request.POST["email"]
        manager_id = int(request.POST["manager_id"])
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        phone =  request.POST["phone"]
        department_id = int(request.POST["department_id"])
        #department_name = request.POST["department_name"]
        created_at =  datetime.datetime.now()
        # updated_at =  datetime.datetime.now()
        
        
        # Fetch department name from the Department table based on department_id
        department = db["Departments"].find_one({"department_id": department_id})
        
        if department:
            department_name = department.get("department_name")  # Extract department name
        else:
            messages.error(request, "Invalid Department ID!")
            return render(request, 'manager_register.html')
        

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'manager_register.html')

        # Check if username already exists in pending or approved managers
        if pending_registrations.find_one({"username": username}) or db['Manager'].find_one({"username": username}):
            messages.error(request, "Username already exists!")
            return render(request, 'manager_register.html')
        
        # Check if manager_id already exists in pending or approved managers
        if pending_registrations.find_one({"manager_id": manager_id}) or db['Manager'].find_one({"manager_id": manager_id}):
            messages.error(request, "Manager ID already exists!")
            return render(request, 'manager_register.html')


        # Hash the password using SHA-256 
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Save manager registration details in pending registrations
        pending_registrations.insert_one({
            "username": username,
            "password": hashed_password,  # Hashed the Password for the security
            "email": email,
            "manager_id": manager_id,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "department_name": department_name,
            "department_id": department_id,
            "created_at": created_at,
            "status": "Pending"
        })

        messages.success(request, "Registration submitted. Waiting for admin approval.")
        return redirect('manager_register')

    return render(request, 'manager_register.html')





# Manager Logout View
def manager_logout(request):
    logout(request)
    return redirect('/manager/login/')




# Manager Dashboard View
# @login_required
def manager_dashboard(request):
    request.session.set_expiry(3600)  # Set session timeout to 1 hour (3600 seconds) for manager
    # Check if the manager is logged in by checking session
    if 'manager_username' not in request.session:
        messages.error(request, "You need to log in to access the dashboard.")
        return redirect('manager_login')  # Redirect to login if not logged in

    # Retrieve the manager's username from the session
    manager_username = request.session['manager_username']

    # Fetch the manager's details from the database
    manager = manager_collection.find_one({"username": manager_username}, {"_id": 0})  # Adjust fields as needed

    if not manager:
        messages.error(request, "Manager not found. Please log in again.")
        return redirect('manager_login')  # Redirect to login if manager not found
    
    
    # ✅ Fetch employees **only** with the same department ID as the manager
    employees = list(employee_collection.find({"department_id": manager.get("department_id")}))

    # ✅ Get employee IDs in this department
    employee_ids = [emp["employee_id"] for emp in employees]  
    
    # ✅ Fetch leave requests **only** for employees in the same department
    leave_requests = list(leave_requests_collection.find({"employee_id": {"$in": employee_ids}}))
    
    
    
    # ✅ Fix: Convert ObjectId to string to avoid template issues
    for leave_request in leave_requests:
        leave_request["id"] = str(leave_request["_id"])
        del leave_request["_id"]
        
        
    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")  # 'approve' or 'reject'

        leave_request = leave_requests_collection.find_one({"_id": ObjectId(request_id)})

        if leave_request:
            new_status = "Approved" if action == "approve" else "Rejected"

            leave_requests_collection.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"status": new_status, "updated_at": datetime.datetime.now()}}
            )

            # Fetch employee details for email notification
            employee = employee_collection.find_one({"employee_id": leave_request["employee_id"]})
            
            if employee:
                send_mail(
                    subject="Leave Request Update",
                    message=f"Your leave request from {leave_request['start_date']} to {leave_request['end_date']} has been {new_status}.",
                    from_email="prakhar9522@gmail.com",
                    recipient_list=[employee.get("email")],
                    fail_silently=True,
                )

            messages.success(request, f"Leave request {new_status} successfully!")

    
    # Fetch data from MongoDB (e.g., employees)
    #employees = employee_collection.find({})  # Ensure this is correct and that data exists
    return render(request, "manager_dashboard.html", {"employees": employees, "manager": manager, "leave_requests": leave_requests})




def manager_edit(request):
    # Check if the manager is logged in
    if 'manager_username' not in request.session:
        messages.error(request, "You need to log in to edit your details.")
        return redirect('manager_login')

    # Retrieve the manager's username from the session
    manager_username = request.session['manager_username']

    # Fetch the manager's details
    manager = manager_collection.find_one({"username": manager_username})
    if not manager:
        messages.error(request, "Manager not found. Please log in again.")
        return redirect('manager_login')

    if request.method == "POST":
        # Update the manager's details from the form data
        updated_data = {
            "username": request.POST.get("username"),
            "manager_id": int(request.POST.get("manager_id")),
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "email": request.POST.get("email"),
            "phone": request.POST.get("phone"),
            "department_id":int(request.POST.get("department_id")),
            "department_name":request.POST.get("department_name"),
            "updated_at": datetime.datetime.now(),
        }

        # Check if the new username or manager_id is already in use
        username_exists = (
            manager_collection.find_one({"username": updated_data["username"], "_id": {"$ne": manager["_id"]}})
            or pending_registrations.find_one({"username": updated_data["username"]})
        )
        manager_id_exists = (
            manager_collection.find_one({"manager_id": updated_data["manager_id"], "_id": {"$ne": manager["_id"]}})
            or pending_registrations.find_one({"manager_id": updated_data["manager_id"]})
        )

        # If username or manager_id is not unique, return an error message
        if username_exists:
            messages.error(request, "The username is already in use. Please choose a different username.")
            return render(request, "manager_edit.html", {"manager": manager})

        if manager_id_exists:
            messages.error(request, "The manager ID is already in use. Please choose a different manager ID.")
            return render(request, "manager_edit.html", {"manager": manager})


        # Update the manager's details in the database
        manager_collection.update_one({"username": manager_username}, {"$set": updated_data})
        messages.success(request, "Your details have been updated successfully.")
        return redirect('manager_dashboard')  # Redirect back to the dashboard

    return render(request, "manager_edit.html", {"manager": manager})





# Add Employee
# @login_required
def manager_add_employee(request):

 
    if request.method == "POST":
        employee_id = int(request.POST["employee_id"])
        
        # Check if the employee ID already exists in the database
        existing_employee = employee_collection.find_one({"employee_id": employee_id})
        pending_employee = db["pending_employees"].find_one({"employee_id": employee_id})
        # pending_employee = db['pending_employees'].find_one({"employee_id": new_employee_id})
        
        if existing_employee:
            # Display an error message if the ID already exists
            messages.error(request, f"Employee ID {employee_id} already exists. Please use a unique ID.")
            return render(request, "manager_add_employee.html")
        
        if pending_employee:
            # Display an error message if the ID already exists
            messages.error(request, f"Employee ID {employee_id} already exists in pending employee. Please use a unique ID.")
            return render(request, "manager_add_employee.html")
        
        
        # Fetch the department name from the department collection using department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "manager_add_employee.html")
        
        department_name = department["department_name"]  # Fetch the department name

        
        # Generate a random password for the new employee
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

       # Hash the password using hashlib.sha256
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        
    
        # If unique, proceed to add the employee
        employee_data = {
            "employee_id": employee_id,
            "first_name": request.POST["first_name"],
            "last_name": request.POST["last_name"],
            "email": request.POST["email"],
            "phone": request.POST["phone"],
            "date_of_birth": datetime.datetime.strptime(request.POST["date_of_birth"], "%Y-%m-%d"),
            "date_of_joining": datetime.datetime.strptime(request.POST["date_of_joining"], "%Y-%m-%d"),
            "department_id": department_id,
            "department_name": department_name,
            "role_id": int(request.POST["role_id"]),
            "salary": float(request.POST["salary"]),
            "status": request.POST["status"],
            "address": request.POST["address"],
            "password": hashed_password,  # Store hashed password
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
            "registration": "Approved"
        }
        employee_collection.insert_one(employee_data)
        
        # Send the password to the employee's email
        subject = "Welcome to the Polysia!"
        message = f"""
        Hello {request.POST['first_name']} {request.POST['last_name']},

        You have been successfully added as an employee to our system by Manager. Below are your login credentials:

        Employee ID: {employee_id}
        Password: {password}

        Please log in and change your password as soon as possible from frogot password with your email.

        Best regards,
        Polysia
        """
        recipient_list = [request.POST["email"]]
        send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)
        
        
        
        messages.success(request, "Employee added and mail sent successfully!")
        return redirect('manager_dashboard')  # Redirect to manager dashboard
        # employees = employee_collection.find({"department_id": department_id})
        # return render(request, "manager_dashboard.html", {"employees": employees})
        # return redirect('/manager/dashboard/')
    return render(request, "manager_add_employee.html")




# Edit Employee
# @login_required
def edit_employee(request, employee_id):

    
    employee = employee_collection.find_one({"employee_id": int(employee_id)})
    
    if not employee:
        messages.error(request, "Employee not found.")
        return redirect('/manager/dashboard/')

    
    if request.method == "POST":
        
        new_employee_id = int(request.POST["employee_id"])

        # Check if the new employee_id already exists in employee_collection or pending_employee_approval
        existing_employee = employee_collection.find_one({"employee_id": new_employee_id})
        pending_employee = db['pending_employees'].find_one({"employee_id": new_employee_id})
        
        if existing_employee and new_employee_id != employee_id:
            messages.error(request, f"Employee ID {new_employee_id} already exists in the system.")
            return render(request, "edit_employee.html", {"employee": employee})
        
        if pending_employee and new_employee_id != employee_id:
            messages.error(request, f"Employee ID {new_employee_id} is pending approval and cannot be used.")
            return render(request, "edit_employee.html", {"employee": employee})
        
        # Fetch department name based on department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "edit_employee.html", {"employee": employee})
        
        department_name = department["department_name"]
        
        updated_data = {
            # "employee_id": int(request.POST["employee_id"]),
            "employee_id": new_employee_id,
            "first_name": request.POST["first_name"],
            "last_name": request.POST["last_name"],
            "email": request.POST["email"],
            "phone": request.POST["phone"],
            # "date_of_birth": datetime.datetime.strptime(request.POST["date_of_birth"], "%Y-%m-%d"),
            # "date_of_joining": datetime.datetime.strptime(request.POST["date_of_joining"], "%Y-%m-%d"),
            "department_id": department_id,
            "department_name": department_name,
            "role_id": int(request.POST["role_id"]),
            "salary": float(request.POST["salary"]),
            "status": request.POST["status"],
            "address": request.POST["address"],
            "updated_at": datetime.datetime.now(),
        }
        employee_collection.update_one({"employee_id": int(employee_id)}, {"$set": updated_data})
        messages.success(request, f"Employee ID {employee_id} updated successfully!")
        return redirect('/manager/dashboard/')
    
    return render(request, "edit_employee.html", {"employee": employee})






# Delete Employee
# @login_required
def delete_employee(request, employee_id):

    
    employee_collection.delete_one({"employee_id": int(employee_id)})
    messages.success(request, f"Employee {employee_id} deleted successfully!")
    return redirect('/manager/dashboard/')





# Password reset request view
def forgot_password(request):
    if request.method == "POST":
        email = request.POST["email"]
        manager = manager_collection.find_one({"email": email})
        
        if manager:
            # Generate a unique token
            token = str(uuid.uuid4())
            # Save the token in the employee document (you can store it in the database with an expiration time)
            manager_collection.update_one(
                {"email": email},
                {"$set": {"reset_token": token}}
            )
            
            # Generate reset link
            reset_link = request.build_absolute_uri(f"/manager/reset_password/{token}/")
            
            # Send email
            send_mail(
                'Password Reset Request',
                f'Click the link below to reset your password: {reset_link}',
                'prakhar9522@gmail.com',
                [email],
                fail_silently=False,
            )
            return render(request, "manager_forgot_password.html", {
                "success_message": "A password reset link has been sent to your email."
            })
            return HttpResponse("A password reset link has been sent to your email.")
        else:
            return render(request, "manager_forgot_password.html", {
                "error_message": "Email not found."
            })
            return HttpResponse("Email not found.")
    
    return render(request, "manager_forgot_password.html")





def reset_password(request, token):
    if request.method == "POST":
        new_password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        
        if new_password != confirm_password:
            return render(request, "manager_reset_password.html", {
                "error_message": "Passwords do not match!",
            })
            return HttpResponse("Passwords do not match.")
        
        # Hash the new password
        hashed_password = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
        
        
        # Find the user by the reset token
        manager = manager_collection.find_one({"reset_token": token})
        if not manager:
            return render(request, "manager_reset_password.html", {
                "error_message": "Invalid or expired reset token.",
            })

        # Update the password in the database
        manager_collection.update_one(
            {"reset_token": token},
            {"$set": {
                "password": hashed_password,
                "updated_at": datetime.datetime.now(),
                "reset_token": None  # Remove the reset token after use
            }}
        )

        messages.success(request, "Password reset successfully! You can now log in with your new password.")
        return redirect("manager_login")

    return render(request, "manager_reset_password.html")