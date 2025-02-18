from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from pymongo import MongoClient
from django.contrib.auth.decorators import login_required
from bson.objectid import ObjectId
from django.contrib import messages
# from django.contrib.auth.models import User
from django.http import HttpResponse
from django.core.mail import send_mail
from collections import defaultdict
import datetime, csv
import random, string, hashlib


# MongoDB connection
#client = MongoClient('mongodb://localhost:27017/')
client = MongoClient('mongodb+srv://Prakhar:Prakhar%40123@cluster0.l2jvk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')

db = client['Employee_Management']
employee_collection = db['Employees']
manager_collection = db['Manager']
department_collection = db['Departments']
leave_requests_collection = db['Leave_Request']
employee_activity_collection = db['Employee_Activity']
employee_attendance_collection = db['Employee_Attendance']
pending_registrations = db['pending_registrations']


# Admin Login
def admin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:  # Only superusers are admins
            if user.is_superuser:
                login(request, user)
                print("Login successful!")
                messages.success(request, "Login successful!")
                return redirect('/admin/dashboard/')  # Redirect to dashboard
            else:
                print("You do not have admin access.")
                messages.error(request, "You do not have admin access.")
                return render(request, "admin_login.html", {"error": "You do not have admin access."})
        else:
            print("Invalid credentials.")
            messages.error(request, "Invalid credentials.")
            return render(request, "admin_login.html", {"error": "Invalid credentials."})
            
    return render(request, "admin_login.html")

# Admin Logout
def admin_logout(request):
    logout(request)
    return redirect('/admin/login/')  # Redirect to the custom login page




# Admin Dashboard View
@login_required
def admin_dashboard(request):
    request.session.set_expiry(3600)  # Set session timeout to 1 hour (3600 seconds) for admins

    # Check if the user is a superuser
    if not request.user.is_superuser:
        messages.error(request, "You need admin access to view this page.")
        return redirect('/admin/login/')  # Redirect to login page
    
    try:
        employees = list(employee_collection.find({}))
        managers = manager_collection.find({})
        departments = department_collection.find({})
        leave_requests = leave_requests_collection.find({})  # Fetch all leave requests
        employee_attendances = list(employee_attendance_collection.find({}))

        
        # Group employees by department_id
        employees_by_department = defaultdict(list)
        # employees_without_department = []

        for employee in employees:
            department_id = employee.get('department_id')
            if department_id:
                employees_by_department[department_id].append(employee)
            # else:
            #     employees_without_department.append(employee)
        
        
    except Exception as e:
        return HttpResponse(f"Error fetching employees or managers: {e}")
    
    
    # Handle Department Creation (POST)
    if request.method == "POST" and "create_department" in request.POST:
        department_name = request.POST.get("department_name")
        department_id = int(request.POST.get("department_id"))

        # Check if department already exists
        existing_department = department_collection.find_one({"department_id": department_id}) or \
                              department_collection.find_one({"department_name": department_name})

        if existing_department:
            messages.error(request, "Department with this ID or name already exists!")
        else:
            # Insert new department into the database
            department_collection.insert_one({
                "department_id": department_id,
                "department_name": department_name
            })
            messages.success(request, "Department created successfully!")
    
    
    # Handle Department Edit (POST)
    elif request.method == "POST" and "edit_department" in request.POST:
        department_id = int(request.POST.get("department_id"))
        new_department_name = request.POST.get("new_department_name")
        
        # Find the department by ID
        department = department_collection.find_one({"department_id": department_id})
        
        if department:
            # Update the department name
            department_collection.update_one(
                {"department_id": department_id},
                {"$set": {"department_name": new_department_name}}
            )
            messages.success(request, f"Department ID {department_id} updated successfully!")
        else:
            messages.error(request, f"Department ID {department_id} not found.")
    
    # Handle Department Deletion (POST)
    elif request.method == "POST" and "delete_department" in request.POST:
        department_id = int(request.POST.get("department_id"))
        
        # Find and delete the department
        department = department_collection.find_one({"department_id": department_id})
        
        if department:
            department_collection.delete_one({"department_id": department_id})
            messages.success(request, f"Department ID {department_id} deleted successfully!")
        else:
            messages.error(request, f"Department ID {department_id} not found.")
    
    
    # Fetch all pending registrations
    pending_list = list(pending_registrations.find())
    pending_employees = list(db['pending_employees'].find())

    if request.method == "POST":
        if "username" in request.POST:
            username = request.POST["username"]
            action = request.POST.get("action", "approve")  # 'approve' or 'reject'
            # Find the pending registration
            manager = pending_registrations.find_one({"username": username})
            
            if manager:
                if action == "approve":
                    # Update the status to "Approved" before moving to approved managers
                    manager["status"] = "Approved"
                    # Move to approved managers
                    db['Manager'].insert_one(manager)
                    # Remove from pending registrations
                    pending_registrations.delete_one({"username": username})
                    messages.success(request, f"Manager {username} approved!")
                
                    # Send an email notification
                    subject = 'Approval Notification' 
                    message = f'Hello {manager["username"]},\n\nYour Manager registration has been approved.\n\nNow you can log in with your credentials.\n\nThank you.' 
                    recipient_list = [manager['email']] 
                    send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)
                    
                    
                elif action == "reject":
                    # Reject Manager
                    pending_registrations.delete_one({"username": username})  # Remove from pending
                    messages.error(request, f"Manager {username} rejected!")

                    # Send rejection email
                    subject = 'Rejection Notification'
                    message = f'Hello {manager["username"]},\n\nWe regret to inform you that your Manager registration has been rejected.\n\nThank you.'

                    # Send email notification
                    recipient_list = [manager['email']] 
                    send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)

        # Handle Employee Approval
        elif "employee_id" in request.POST:
            employee_id = int(request.POST["employee_id"])
            action = request.POST.get("action", "approve")  # 'approve' or 'reject'
            # Find the pending employee registration
            employee = db['pending_employees'].find_one({"employee_id": employee_id})
            if employee:
                if action == "approve":
                    # Update the status to "Approved"
                    employee["registration"] = "Approved"
                    # Move to the main Employees collection
                    db['Employees'].insert_one(employee)
                    # Remove from pending registrations
                    db['pending_employees'].delete_one({"employee_id": employee_id})
                    messages.success(request, f"Employee {employee_id} approved!")
                    
                    # Send an email notification to the employee
                    subject = 'Approval Notification'
                    message = f'Hello {employee["first_name"]} {employee["last_name"]},\n\nYour Employee registration has been approved by Admin.\n\nNow you can login with your credentials.\n\nThank you.'
                    recipient_list = [employee['email']]
                    send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)
                
                elif action == "reject":
                    # Reject Employee
                    db['pending_employees'].delete_one({"employee_id": employee_id})  # Remove from pending
                    messages.error(request, f"Employee {employee_id} rejected!")

                    # Send rejection email
                    subject = 'Rejection Notification'
                    message = f'Hello {employee["first_name"]} {employee["last_name"]},\n\nWe regret to inform you that your Employee registration has been rejected.\n\nThank you.'

                    # Send email notification
                    recipient_list = [employee['email']]  # Assuming the email is stored in the 'email' field
                    send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)


    return render(request, 'admin_dashboard.html', {
        'pending_list': pending_list,
        'pending_employees': pending_employees,
        'employees': employees,
        'employees_by_department': dict(employees_by_department),
        # 'employees_without_department': employees_without_department,
        'managers': managers,
        'departments': departments,
        'leave_requests': leave_requests,  # Pass leave data to template
        'employee_attendances': employee_attendances,
    })
        
        




# Add Employee
# @login_required
def add_employee_admin(request):
    if not request.user.is_superuser:
        return redirect('/admin/login/')
    
    if request.method == "POST":
        employee_id = int(request.POST["employee_id"])
        
        # Check if the employee ID already exists in the database
        existing_employee = employee_collection.find_one({"employee_id": employee_id})
        
        if existing_employee:
            # Display an error message if the ID already exists
            messages.error(request, f"Employee ID {employee_id} already exists. Please use a unique ID.")
            return render(request, "add_admin_employee.html")


        # Fetch the department name from the department collection using department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "add_admin_employee.html")
        
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
            "date_of_birth": datetime.strptime(request.POST["date_of_birth"], "%Y-%m-%d"),
            "date_of_joining": datetime.strptime(request.POST["date_of_joining"], "%Y-%m-%d"),
            "department_id": department_id,
            "department_name": department_name,
            "role_id": int(request.POST["role_id"]),
            "salary": float(request.POST["salary"]),
            "status": request.POST["status"],
            "address": request.POST["address"],
            "password": hashed_password,  # Store hashed password
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "registration": "Approved"
        }
        employee_collection.insert_one(employee_data)
        
        # Send the password to the employee's email
        subject = "Welcome to the Polysia!"
        message = f"""
        Hello {request.POST['first_name']} {request.POST['last_name']},

        You have been successfully added as an Employee to our system by Admin. Below are your login credentials:

        Employee ID: {employee_id}
        Password: {password}

        Please log in and change your password as soon as possible from frogot password with your email.

        Best regards,
        Polysia
        """
        recipient_list = [request.POST["email"]]
        send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)
        
        
        messages.success(request, "Employee added and mail sent successfully!")
        return redirect('/admin/dashboard/')
    
    return render(request, "add_admin_employee.html")





# Edit Employee
# @login_required
def edit_employee(request, employee_id):
    if not request.user.is_superuser:
        return redirect('/admin/login/')
    
    employee = employee_collection.find_one({"employee_id": int(employee_id)})
    
    if not employee:
        messages.error(request, "Employee not found.")
        return redirect('/admin/dashboard/')
    
    if request.method == "POST":
        # Fetch department name based on department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "edit_admin_employee.html", {"employee": employee})
        
        department_name = department["department_name"]

        # Prepare the updated data
        updated_data = {
            "employee_id": int(request.POST["employee_id"]),
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
            "updated_at": datetime.now(),
        }
        employee_collection.update_one({"employee_id": int(employee_id)}, {"$set": updated_data})
        messages.success(request, "Employee Updated successfully!")
        return redirect('/admin/dashboard/')
    
    return render(request, "edit_admin_employee.html", {"employee": employee})

# Delete Employee
# @login_required
def delete_employee(request, employee_id):
    if not request.user.is_superuser:
        return redirect('/admin/login/')
    
    employee_collection.delete_one({"employee_id": int(employee_id)})
    messages.success(request, f"Employee {employee_id} deleted successfully!")
    return redirect('/admin/dashboard/')













# Add Manager
# @login_required
def add_manager(request):
    if not request.user.is_superuser:
        return redirect('/admin/login/')
    
    if request.method == "POST":
        manager_id = int(request.POST["manager_id"])
        username = request.POST.get("username")
        
         # Check if the manager ID or username already exists in either the `manager` or `pending` collections
        manager_id_exists = (
            manager_collection.find_one({"manager_id": manager_id}) or
            pending_registrations.find_one({"manager_id": manager_id})
        )
        username_exists = (
            manager_collection.find_one({"username": username}) or
            pending_registrations.find_one({"username": username})
        )
        
        if manager_id_exists:
            messages.error(request, f"Manager ID {manager_id} already exists. Please use a unique ID.")
            return render(request, "add_manager.html")

        if username_exists:
            messages.error(request, f"Username '{username}' is already in use. Please choose a different username.")
            return render(request, "add_manager.html")
        
        
        # Fetch the department name from the department collection using department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "add_manager.html")
        
        department_name = department["department_name"]  # Fetch the department name
        
         # Generate a random password for the new employee
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # Hash the password using hashlib.sha256
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # If unique, proceed to add the manager
        manager_data = {
            "username": request.POST.get("username"),
            "manager_id": manager_id,
            "first_name": request.POST["first_name"],
            "last_name": request.POST["last_name"],
            "email": request.POST["email"],
            "phone": request.POST["phone"],
            "password": hashed_password,  # Store hashed password
            "department_id": department_id,
            "department_name": department_name,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        manager_collection.insert_one(manager_data)
        
        # Send the password to the employee's email
        subject = "Welcome to the Polysia!"
        message = f"""
        Hello {request.POST['first_name']} {request.POST['last_name']},

        You have been successfully added as an Manager to our system by Admin. Below are your login credentials:

        User Name: {username}
        Password: {password}

        Please log in and change your password as soon as possible from frogot password with your email.

        Best regards,
        Polysia
        """
        recipient_list = [request.POST["email"]]
        send_mail(subject, message, 'prakhar9522@gmail.com', recipient_list)
        
        
        messages.success(request, "Manager added and mail sent successfully!")
        return redirect('/admin/dashboard/')
    
    return render(request, "add_manager.html")






# Edit Manager
# @login_required
def edit_manager(request, manager_id):
    if not request.user.is_superuser:
        return redirect('/admin/login/')
    
    manager = manager_collection.find_one({"manager_id": int(manager_id)})
    if request.method == "POST":
        # Fetch department name based on department_id
        department_id = int(request.POST["department_id"])
        department = department_collection.find_one({"department_id": department_id})
        
        if not department:
            messages.error(request, f"Department ID {department_id} not found.")
            return render(request, "edit_manager.html", {"manager": manager})
        
        department_name = department["department_name"]
        updated_data = {
            # "manager_id": manager_id,
            "manager_id": int(request.POST["manager_id"]),
            "first_name": request.POST["first_name"],
            "last_name": request.POST["last_name"],
            "email": request.POST["email"],
            "phone": request.POST["phone"],
            "department_id": department_id,
            "department_name": department_name,
            "updated_at": datetime.now(),
        }
        manager_collection.update_one({"manager_id": int(manager_id)}, {"$set": updated_data})
        messages.success(request, "Manager updated successfully!")
        return redirect('/admin/dashboard/')
    return render(request, "edit_manager.html", {"manager": manager})




# Delete Manager
# @login_required
def delete_manager(request, manager_id):
    if not request.user.is_superuser:
        return redirect('/admin/login/')
    
    manager_collection.delete_one({"manager_id": int(manager_id)})
    messages.success(request, f"Manager {manager_id} deleted successfully!")
    return redirect('/admin/dashboard/')










# @login_required
def employee_leaves(request):
    if not request.user.is_superuser:
        messages.error(request, "You need admin access to view this page.")
        return redirect('/admin/login/')  # Redirect unauthorized users

    try:
        leave_requests = list(leave_requests_collection.find({}).sort([("_id", -1)]))  # Fetch leave requests
    except Exception as e:
        return HttpResponse(f"Error fetching leave requests: {e}")

    return render(request, 'employee_leaves.html', {'leave_requests': leave_requests})







# @login_required
# def employee_attendance_details(request):
#     """ View to display all employee attendance details """
#     if not request.user.is_superuser:
#         messages.error(request, "You need admin access.")
#         return redirect('admin_dashboard')

#     # Fetch all attendance records from the database
#     employee_attendances = list(db['Employee_Attendance'].find({}))

#     return render(request, "employee_attendance_list.html", {"attendances": employee_attendances})


from collections import defaultdict
from datetime import datetime

# @login_required
def employee_attendance_details(request):
    """ View to display all employee attendance details grouped by date """
    if not request.user.is_superuser:
        messages.error(request, "You need admin access.")
        return redirect('admin_dashboard')

    # Fetch all attendance records from the database
    employee_attendances = list(db['Employee_Attendance'].find({}).sort([("_id", -1)]))

    # Group attendance records by date
    attendance_by_date = defaultdict(list)
    for record in employee_attendances:
        start_time = record.get('start_time')
        if start_time:
            # Check if start_time is already a datetime object
            if isinstance(start_time, datetime):
                date = start_time.strftime('%Y-%m-%d')
            else:
                # If start_time is a string, parse it into a datetime object
                try:
                    start_datetime = datetime.fromisoformat(start_time)
                    date = start_datetime.strftime('%Y-%m-%d')
                except (TypeError, ValueError):
                    # Handle invalid or unexpected formats
                    continue
            # Add the record to the corresponding date group
            attendance_by_date[date].append(record)

    # Convert defaultdict to a regular dict for the template
    attendance_by_date = dict(attendance_by_date)

    return render(request, "employee_attendance_list.html", {"attendance_by_date": attendance_by_date})




from datetime import datetime  # Ensure this is imported

# @login_required
def download_attendance_csv(request, employee_id):
    """ View to download all employee attendance data as a CSV file """
    if not request.user.is_superuser:
        messages.error(request, "You need admin access to download the file.")
        return redirect('admin_dashboard')

    # Fetch attendance data
    employee_attendances = list(db['Employee_Attendance'].find({"employee_id": employee_id}).sort([("_id", -1)]))

    # Create the HTTP response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employee_attendances.csv"'

    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow(["Employee ID", "Employee Name", "Check-in Time", "Check-out Time", "Status"])

    from datetime import datetime

    def format_datetime(dt):
        """ Helper function to format datetime """
        if dt:
            # Ensure that dt is an instance of datetime
            if isinstance(dt, datetime):  # Check if dt is a datetime object
                dt_obj = dt
            else:
                # Attempt to parse the string date if it's not a datetime object
                try:
                    dt_obj = datetime.strptime(str(dt), "%Y-%m-%dT%H:%M:%S.%f%z")
                except ValueError:
                    return ""  # Return empty string if the date can't be parsed
            
            return dt_obj.strftime("%b. %d, %Y, %I:%M %p")  # Format as "Feb. 05, 2025, 08:30 AM"
        return ""




    # Write attendance data
    for record in employee_attendances:
        formatted_start_time = format_datetime(record.get("start_time"))
        formatted_end_time = format_datetime(record.get("end_time"))

        writer.writerow([
            record.get("employee_id", ""),
            record.get("employee_name", ""),
            formatted_start_time,
            formatted_end_time,
            record.get("attendance_type", "")
        ])

    return response














# @login_required
def employee_activity(request):
    """ View to display login and logout activity for a specific employee """
    if not request.user.is_superuser:
        messages.error(request, "You need admin access.")
        return redirect('admin_dashboard')

    employee_activities = None  # Placeholder for activity data

    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')

        # Check if employee_id is provided and it's valid
        if employee_id:
            try:
                employee_activities = list(db['Employee_Activity'].find({"employee_id": int(employee_id)}).sort([("_id", -1)]))

                # Check if we have data for the employee
                if not employee_activities:
                    messages.error(request, "No activity found for this employee.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "Please enter a valid Employee ID.")

    return render(request, "employee_activity.html", {
        'employee_activities': employee_activities
    })
    
    





from datetime import datetime  # Ensure this is imported

# @login_required
def download_employee_activity_csv(request, employee_id):
    """ View to download employee activity data as a CSV file """
    if not request.user.is_superuser:
        messages.error(request, "You need admin access to download the file.")
        return redirect('admin_dashboard')

    # Fetch the employee activity data
    employee_activities = list(db['Employee_Activity'].find({"employee_id": employee_id}).sort([("_id", -1)]))

    # Create the HTTP response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="employee_{employee_id}_activity.csv"'

    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow(["Employee ID", "Action", "Email", "Timestamp"])
    
    

    def format_datetime(dt):
        """ Helper function to format datetime """
        if dt:
            # Check if dt is a string that needs to be parsed into a datetime object
            if isinstance(dt, str):
                try:
                    dt_obj = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f%z")
                except ValueError:
                    return ""  # Return empty string if the date can't be parsed
            elif isinstance(dt, datetime):
                dt_obj = dt
            else:
                return ""  # Return empty string if dt is not a recognized type

            return dt_obj.strftime("%b. %d, %Y, %I:%M %p")  # Format as "Feb. 05, 2025, 08:30 AM"
        return ""


    # Write attendance data
    for record in employee_activities:
        formatted_timestamp = format_datetime(record.get("timestamp"))

        writer.writerow([
            record.get("employee_id", ""),
            record.get("action", ""),
            record.get("email", ""),
            formatted_timestamp
        ])

    return response






