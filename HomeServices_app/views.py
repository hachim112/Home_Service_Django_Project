from datetime import datetime, timedelta
import random
from django.db.models import Q, Avg
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.db import transaction
from .models import Response, State, workers, users, ServiceCatogarys, Country, City, Feedback, ServiceRequests, WorkerAvailability
from .forms import stateform
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from .models import Country, State, City  # Adjust based on your actual models
import time


class Commenlib:
    def __init__(self):
        self.DEFAULT_REDIRECT_PATH={'ROOT':'/'}

common_lib = Commenlib()

def check_worker_availability(worker, date_str, time_slot):
    """
    Check if a worker is available at the specified date and time slot.
    
    Args:
        worker: The worker object to check
        date_str: Date string in YYYY-MM-DD format
        time_slot: 'morning', 'afternoon', or 'evening'
        
    Returns:
        True if available, False otherwise
    """
    from datetime import datetime
    
    # Convert string date to datetime object
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # If date is invalid, assume worker is not available
        return False
    
    try:
        # Check if there's an availability record for this date
        availability = WorkerAvailability.objects.get(worker=worker, date=date_obj)
        
        # Check the specific time slot
        if time_slot == 'morning':
            if not availability.morning_available:
                return False
        elif time_slot == 'afternoon':
            if not availability.afternoon_available:
                return False
        elif time_slot == 'evening':
            if not availability.evening_available:
                return False
        else:
            # Invalid time slot
            return False
            
    except WorkerAvailability.DoesNotExist:
        # If no record exists, assume all slots are available by default
        pass
    
    # Check if the worker has any conflicting appointments at the same time slot
    # This includes both specifically assigned requests and accepted requests
    existing_appointments = Response.objects.filter(
        assigned_worker=worker,
        scheduled_date=date_obj,
        scheduled_time=time_slot,
        status=False  # Only check pending appointments
    ).exists()
    
    # Also check if there are any pending service requests that this worker has been specifically chosen for
    specifically_chosen = Response.objects.filter(
        assigned_worker=worker,
        requests__preferred_date=date_obj,
        requests__preferred_time=time_slot,
        worker_specifically_chosen=True,
        status=False
    ).exists()
    
    # If there are no conflicting appointments, the worker is available
    return not (existing_appointments or specifically_chosen)

# Add this AJAX endpoint view function
def check_worker_availability_ajax(request):
    """
    AJAX endpoint to check worker availability
    """
    if request.method == 'GET':
        worker_id = request.GET.get('worker_id')
        date_str = request.GET.get('date')
        time_slot = request.GET.get('time_slot')
        
        if not all([worker_id, date_str, time_slot]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        
        try:
            worker = workers.objects.get(id=worker_id)
            is_available = check_worker_availability(worker, date_str, time_slot)
            
            return JsonResponse({
                'worker_id': worker_id,
                'available': is_available
            })
        except workers.DoesNotExist:
            return JsonResponse({'error': 'Worker not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

# Create your views here.
class Login(View):
    def get(self, request):
        return render(request, 'login.html')
    def post(self,request):
        username = request.POST['uname']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        print(user)
        # print(user.username)

        if user is not None:
            login(request, user)
            if user.is_superuser and user.is_staff:
                return  HttpResponseRedirect('/admmin_home')
                # return render(request, 'adminhome.html')

            elif user.is_staff:
                return HttpResponseRedirect('/workers_home')
            else:
                return HttpResponseRedirect('/index')
        else:
            return render(request, 'login.html', {'error_msg': "Invalid credentials."})

def logout_view(request):
    logout(request)
    # return redirect('login')
    return redirect('index')  # Redirect to home page after logout

class User_Register(View):
    def get(self, request):
        return render(request, 'user_register.html')

    def post(self,request):
        first_name = request.POST.get('firstname')
        last_name = request.POST.get('lastname')
        email = request.POST.get('email')
        contact_number = request.POST.get('contactnumber')
        address = request.POST.get('address')
        profile_pics = request.FILES.get('profile_pic')
        gender = request.POST.get('gender')
        # user_type = request.POST.get('usertype')
        password = request.POST.get('password')
        cpassword = request.POST.get('cpassword')
        # user_type= 3
        # Check if passwords match
        if password == cpassword:
            new_user = User.objects.create(
                username=email,
                email=email,
                password=make_password(password),
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                is_staff=False,
            )


            users.objects.create(admin=new_user, Address=address, gender=gender, contact_number=contact_number,profile_pic=profile_pics)
            return render(request, 'login.html', {'msg': "Addd succsfully!"})


        else:
            return render(request, 'user_register.html', {'msg': "Passwords do not match!"})

        return render(request, 'user_register.html', {'msg': "Something went wrong"})



class Worker_Register(View):
    def get(self, request):
        designations = ServiceCatogarys.objects.all()
        context = {
            'designations': designations,
        }
        return render(request, 'workers_registration.html', context)

    def post(self, request):
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        email = request.POST.get('email')
        contactnumber = request.POST.get('contactnumber')
        dob = request.POST.get('dob')
        gender = request.POST.get('gender')
        city = request.POST.get('city')
        address = request.POST.get('address')
        designation = request.POST.get('designation')
        profile_pic = request.FILES.get('profile_pic')
        password = request.POST.get('password')
        cpassword = request.POST.get('cpassword')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            designations = ServiceCatogarys.objects.all()
            context = {
                'designations': designations,
                'msg': '<div class="alert alert-danger">This email is already in use. Please use a different email address.</div>',
                # Preserve form data to avoid re-entering everything
                'form_data': {
                    'firstname': firstname,
                    'lastname': lastname,
                    'email': email,
                    'contactnumber': contactnumber,
                    'dob': dob,
                    'gender': gender,
                    'city': city,
                    'address': address,
                    'designation': designation
                }
            }
            return render(request, 'workers_registration.html', context)
        
        # Check if passwords match
        if password == cpassword:
            try:
                # Create new user
                new_user = User.objects.create(
                    username=email,
                    email=email,
                    password=make_password(password),
                    first_name=firstname,
                    last_name=lastname,
                    is_active=True,
                    is_staff=True,
                )

                # Create worker profile
                new_worker = workers(
                    admin=new_user, 
                    contact_number=contactnumber, 
                    dob=dob, 
                    Address=address, 
                    city=city,
                    gender=gender, 
                    designation=designation, 
                    profile_pic=profile_pic,
                    acc_activation=False, 
                    avalability_status=True
                )
                new_worker.save()

                return render(request, 'login.html', {'msg': '<div class="alert alert-success">Registration successful! You can now login.</div>'})
            
            except Exception as e:
                # Handle any other errors
                designations = ServiceCatogarys.objects.all()
                context = {
                    'designations': designations,
                    'msg': f'<div class="alert alert-danger">An error occurred: {str(e)}</div>',
                    'form_data': {
                        'firstname': firstname,
                        'lastname': lastname,
                        'email': email,
                        'contactnumber': contactnumber,
                        'dob': dob,
                        'gender': gender,
                        'city': city,
                        'address': address,
                        'designation': designation
                    }
                }
                return render(request, 'workers_registration.html', context)
        else:
            # Passwords don't match
            designations = ServiceCatogarys.objects.all()
            context = {
                'designations': designations,
                'msg': '<div class="alert alert-danger">Passwords do not match!</div>',
                'form_data': {
                    'firstname': firstname,
                    'lastname': lastname,
                    'email': email,
                    'contactnumber': contactnumber,
                    'dob': dob,
                    'gender': gender,
                    'city': city,
                    'address': address,
                    'designation': designation
                }
            }
            return render(request, 'workers_registration.html', context)


class home(View):  # Remove LoginRequiredMixin
    def get(self, request):
        services = ServiceCatogarys.objects.all()
        feedbacks = Feedback.objects.select_related('User', 'Employ', 'Employ__admin').all()
        all_services = list(ServiceCatogarys.objects.all())  # Convert QuerySet to a list
        selected_services = random.sample(all_services, min(len(all_services), 6))  # Select up to 6 random services
        print('services:', services)
        context = {
            'services': services,
            'feedbacks': feedbacks,
            'selected_services': selected_services,
        }
        return render(request, 'userpages/index.html', context)

class about(View):  # Remove LoginRequiredMixin
    def get(self,request):
        return render(request, 'userpages/about.html')
    
class services(View):  # Remove LoginRequiredMixin
    def get(self,request):
        services = ServiceCatogarys.objects.all()
        feedbacks = Feedback.objects.select_related('User').all()
        all_services = list(ServiceCatogarys.objects.all())  # Convert QuerySet to a list
         # Select 6 random services
        print('services:', services)
        context = {
            'services': services,
            'feedbacks': feedbacks,
        }
        return render(request,'userpages/service.html',context)
class bookservice(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        services = ServiceCatogarys.objects.get(id=id)
        city=City.objects.all()
        
        # Fetch workers who can perform this service
        available_workers = workers.objects.filter(
            designation=services.Name,
            acc_activation=True,
            avalability_status=True
        )
        
        # Calculate completed tasks and ratings for each worker
        for worker in available_workers:
            # Count completed tasks
            completed_tasks = Response.objects.filter(
                assigned_worker=worker,
                status=True
            ).count()
            worker.completed_tasks = completed_tasks
            
            # Calculate average rating
            worker_ratings = Feedback.objects.filter(Employ=worker)
            if worker_ratings.exists():
                avg_rating = worker_ratings.aggregate(Avg('Rating'))['Rating__avg']
                worker.rating = avg_rating
                # Calculate star display (for full and half stars)
                worker.rating_stars = int(avg_rating)
                worker.rating_stars_half = worker.rating_stars + 0.5 if avg_rating - worker.rating_stars >= 0.3 else worker.rating_stars
            else:
                worker.rating = 0
                worker.rating_stars = 0
                worker.rating_stars_half = 0
        
        print(services.Name)
        context = {
            'services': services,
            'city': city,
            'available_workers': available_workers,
        }
        return render(request,'userpages/servicebook.html',context)

    # Find the post method in the bookservice class and replace it with this implementation
    
    def post(self, request, id):
        user_id = request.user.id
        user = users.objects.get(admin=user_id)
        problem_description = request.POST.get('Problem_Description')
        service_id = ServiceCatogarys.objects.get(id=id)
        address = request.POST.get('Address')
        city_id = request.POST.get('city')
        pin = request.POST.get('Pincode')
        house_no = request.POST.get('House_No')
        landmark = request.POST.get('landmark')
        contact = request.POST.get('contact')
        
        # Get date and time preferences
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        
        # Get worker selection type and selected worker if applicable
        worker_selection = request.POST.get('worker_selection', 'autofast')
        selected_worker_id = request.POST.get('selected_worker') if worker_selection == 'specific' else None

        # Check worker availability based on selection type
        if worker_selection == 'specific' and selected_worker_id:
            # Check if the specific worker is available at the requested time
            selected_worker = workers.objects.get(id=selected_worker_id)
            is_available = check_worker_availability(selected_worker, preferred_date, preferred_time)
        
            if not is_available:
                messages.error(request, f"{selected_worker.admin.first_name} {selected_worker.admin.last_name} is not available at the selected date and time. Please choose a different time or worker.")
                return self.get(request, id)  # Return to the form with error message
        else:
            # For AutoFast, check if any eligible workers are available
            eligible_workers = workers.objects.filter(
                designation=service_id.Name,
                acc_activation=True,
                avalability_status=True
            )
        
            available_workers = []
            for worker in eligible_workers:
                if check_worker_availability(worker, preferred_date, preferred_time):
                    available_workers.append(worker)
        
            if not available_workers:
                messages.error(request, "No workers are available at the selected date and time. Please choose a different time.")
                return self.get(request, id)  # Return to the form with error message

        # Create a new ServiceRequests instance and save it
        service_request = ServiceRequests(
            user=user,
            Problem_Description=problem_description,
            service=service_id,
            Address=address,
            city_id=city_id,
            pin=pin,
            House_No=house_no,
            landmark=landmark,
            contact=contact,
            preferred_date=preferred_date,
            preferred_time=preferred_time
        )
        
        # If a specific worker was selected, create a response record immediately
        if worker_selection == 'specific' and selected_worker_id:
            selected_worker = workers.objects.get(id=selected_worker_id)
        
            # For specifically chosen workers, we still mark the request as unassigned
            # until the worker accepts it
            service_request.status = False
            service_request.save()
        
            # Create response with worker_specifically_chosen=True
            Response.objects.create(
                requests=service_request,
                assigned_worker=selected_worker,
                status=False,  # Not completed yet
                worker_specifically_chosen=True,
                scheduled_date=preferred_date,
                scheduled_time=preferred_time
            )
        
            messages.success(request, f"Your service request has been sent to {selected_worker.admin.first_name} {selected_worker.admin.last_name}. Waiting for acceptance.")
        else:
            # For autofast requests, mark as unassigned and don't create any response records
            service_request.status = False
            service_request.save()
        
            messages.success(request, f"Your service request has been sent to {len(available_workers)} available workers. The first to accept will be assigned.")

        # Redirect to appointment history page
        return HttpResponseRedirect('/Viewappointment_history')

class admmin_home(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        from django.db.models import Count, Avg
        from datetime import timedelta
        import calendar


      
    
        # Basic stats (already in your code)
        total_requests = ServiceRequests.objects.count()
        completed_requests = Response.objects.filter(status=True).count()
        pending_requests = Response.objects.filter(status=False).count()
        total_users = users.objects.count()
        total_workers = workers.objects.count()
        
        # Service Request Trends - Last 6 months
        request_trends = [
            {'month': 'Jan', 'count': 0},
        
        ]
        current_date = datetime.now()
        
        # Get data for the last 6 months
        for i in range(5, -1, -1):
            # Calculate the month
            month_date = current_date - timedelta(days=30 * i)
            month_name = month_date.strftime('%b')  # Short month name
            month_number = month_date.month
            year = month_date.year
            
            # Count requests for this month - using dateofrequest instead of created_at
            month_count = ServiceRequests.objects.filter(
                dateofrequest__year=year,
                dateofrequest__month=month_number
            ).count()
            
            request_trends.append({
                'month': month_name,
                'count': month_count
            })
        
        # Service Distribution by Category
        service_categories = []
        services = ServiceCatogarys.objects.all()
        
        # Define colors for the chart
        colors = [
            'rgba(78, 205, 196, 0.8)',
            'rgba(40, 167, 69, 0.8)',
            'rgba(23, 162, 184, 0.8)',
            'rgba(255, 193, 7, 0.8)',
            'rgba(108, 117, 125, 0.8)',
            'rgba(220, 53, 69, 0.8)',
            'rgba(111, 66, 193, 0.8)',
            'rgba(232, 62, 140, 0.8)'
        ]
        
        # Count requests for each service category
        for i, service in enumerate(services):
            color_index = i % len(colors)
            request_count = ServiceRequests.objects.filter(service=service).count()
            
            service_categories.append({
                'name': service.Name,
                'count': request_count,
                'color': colors[color_index]
            })
        
        # Top Workers - Based on ratings from feedback
        top_workers_data = []
        worker_colors = ['primary', 'success', 'info', 'warning', 'danger', 'purple', 'pink', 'orange']
        
        # Get workers with feedback and calculate average rating
        worker_ratings = {}
        for feedback in Feedback.objects.all():
            worker_id = feedback.Employ.id
            if worker_id not in worker_ratings:
                worker_ratings[worker_id] = {'total': 0, 'count': 0}
            
            worker_ratings[worker_id]['total'] += feedback.Rating
            worker_ratings[worker_id]['count'] += 1
        
        # Calculate average ratings and create worker data
        for worker_id, rating_data in worker_ratings.items():
            if rating_data['count'] > 0:
                worker = workers.objects.get(id=worker_id)
                avg_rating = rating_data['total'] / rating_data['count']
                
                color_index = len(top_workers_data) % len(worker_colors)
                top_workers_data.append({
                    'name': worker.admin.first_name or worker.admin.username,
                    'last_name': worker.admin.last_name or '',
                    'service_category': worker.designation,
                    'rating': round(avg_rating, 1),
                    'color': worker_colors[color_index]
                })
        
        # Sort workers by rating (highest first) and limit to top 5
        top_workers_data = sorted(top_workers_data, key=lambda x: x['rating'], reverse=True)[:5]
        
        # Recent Activity
        recent_activities = []
        
        # Recent completed requests
        recent_completed = Response.objects.filter(status=True).order_by('-id')[:3]
        for resp in recent_completed:
            recent_activities.append({
                'user_name': resp.assigned_worker.admin.get_full_name() or resp.assigned_worker.admin.username,
                'description': f"completed a {resp.requests.service.Name} service request",
                'timestamp': resp.requests.dateofrequest  # Using dateofrequest instead of created_at
            })
        
        # Recent accepted requests
        recent_accepted = Response.objects.filter(status=False).order_by('-id')[:3]
        for resp in recent_accepted:
            recent_activities.append({
                'user_name': resp.assigned_worker.admin.get_full_name() or resp.assigned_worker.admin.username,
                'description': f"accepted a {resp.requests.service.Name} service request",
                'timestamp': resp.requests.dateofrequest  # Using dateofrequest instead of created_at
            })
        
        # Recent new workers
        recent_workers = workers.objects.order_by('-id')[:2]
        for worker in recent_workers:
            recent_activities.append({
                'user_name': worker.admin.get_full_name() or worker.admin.username,
                'description': "joined as a new worker",
                'timestamp': worker.admin.date_joined
            })
        
        # Recent new users
        recent_users = users.objects.order_by('-id')[:2]
        for user in recent_users:
            recent_activities.append({
                'user_name': user.admin.get_full_name() or user.admin.username,
                'description': "registered as a new user",
                'timestamp': user.admin.date_joined
            })
        
        # Sort activities by timestamp (newest first) and limit to 5
        recent_activities = sorted(recent_activities, key=lambda x: x['timestamp'], reverse=True)[:5]
        
        context = {
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'total_users': total_users,
            'total_workers': total_workers,
            'request_trends': request_trends,
            'service_categories': service_categories,
            'top_workers': top_workers_data,
            'recent_activities': recent_activities
        }
        
        return render(request, 'adminpages/adminhompage.html', context)

class workers_home(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        # Get the current worker's ID
        worker_id = request.user.id
        worker = workers.objects.get(admin=worker_id)
        
        # Get worker-specific statistics
        # 1. Completed requests by this worker
        completed_requests = Response.objects.filter(
            assigned_worker=worker,
            status=True
        ).count()
        
        # 2. Pending requests assigned to this worker
        pending_requests = Response.objects.filter(
            assigned_worker=worker,
            status=False
        ).count()
        
        # 3. Total requests assigned to this worker (completed + pending)
        total_requests = completed_requests + pending_requests
        
        # 4. Count unique clients this worker has served
        client_ids = Response.objects.filter(
            assigned_worker=worker
        ).values_list('requests__user', flat=True).distinct()
        total_clients = len(client_ids)
        
        # 5. Count available requests that match worker's designation
        available_count = ServiceRequests.objects.filter(
            service__Name=worker.designation,
            status=False
        ).exclude(
            id__in=Response.objects.filter(worker_specifically_chosen=True).values_list('requests_id', flat=True)
        ).count()
        
        # Get recent activities
        recent_activities = []
        
        # Recent completed tasks
        recent_completed = Response.objects.filter(
            assigned_worker=worker,
            status=True
        ).order_by('-Date')[:3]
        
        for response in recent_completed:
            recent_activities.append({
                'type': 'completed',
                'title': f"Completed: {response.requests.service.Name}",
                'description': f"You completed a service request for {response.requests.user.admin.first_name} {response.requests.user.admin.last_name}",
                'time': response.Date.strftime("%b %d, %Y at %I:%M %p")
            })
        
        # Recent assigned tasks
        recent_assigned = Response.objects.filter(
            assigned_worker=worker,
            status=False
        ).order_by('-id')[:3]
        
        for response in recent_assigned:
            recent_activities.append({
                'type': 'assigned',
                'title': f"Assigned: {response.requests.service.Name}",
                'description': f"You were assigned a new service request from {response.requests.user.admin.first_name} {response.requests.user.admin.last_name}",
                'time': response.requests.dateofrequest.strftime("%b %d, %Y at %I:%M %p")
            })
        
        # Recent feedback
        recent_feedback = Feedback.objects.filter(
            Employ=worker
        ).order_by('-Date')[:3]
        
        for feedback in recent_feedback:
            stars = "★" * int(feedback.Rating) + "☆" * (5 - int(feedback.Rating))
            recent_activities.append({
                'type': 'feedback',
                'title': f"New Feedback: {stars}",
                'description': f"{feedback.Description[:50]}{'...' if len(feedback.Description) > 50 else ''}",
                'time': feedback.Date.strftime("%b %d, %Y at %I:%M %p")
            })
        
        # Sort all activities by time (newest first)
        recent_activities = sorted(
            recent_activities, 
            key=lambda x: datetime.strptime(x['time'], "%b %d, %Y at %I:%M %p"), 
            reverse=True
        )[:5]  # Limit to 5 most recent activities
        
        context = {
            'completed_requests': completed_requests,
            'pending_requests': pending_requests,
            'total_requests': total_requests,
            'total_clients': total_clients,
            'available_count': available_count,
            'recent_activities': recent_activities,
        }
        return render(request, 'workerpages/Workerhompage.html', context)




class manageworker(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        workers_records=workers.objects.all()
        context={'workers_records':workers_records}
        return render(request,'adminpages/Manage_Workers.html',context)

class verify_worker(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request, action, id):
        btn = workers.objects.get(id=id)
        if action == 'active' and btn.acc_activation == False:
            workers.objects.filter(id=id).update(acc_activation=True)
            return HttpResponseRedirect('/manageworker')
        else:
            return HttpResponse("Something Went Wrong")
        
        return HttpResponseRedirect('/manageworker')

class manageusers(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        users_records=users.objects.all()
        context={'users_records':users_records}
        return render(request,'adminpages/View_Users.html',context)


class AddCountry(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        return render(request, 'country.html')

    def post(self, request):
        country_name = request.POST.get('name')
        Country.objects.create(name=country_name)
        return HttpResponseRedirect('/ManageCountry')

class ManageCountry(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        Country_record=Country.objects.all()
        context={
            'Country_record':Country_record
        }
        return render(request,'adminpages/Manage_Country.html',context)
class DeleteCountry(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        data=Country.objects.get(id=id)
        data.delete()
        return HttpResponseRedirect('/ManageCountry')



class ManageState(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        State_record=State.objects.all()
        context={
            'State_record':State_record
        }
        return render(request,'adminpages/ManageState.html',context)

class AddState(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        country_recorsd = Country.objects.all()
        return render(request, 'state.html', {'country_recorsd': country_recorsd})

    def post(self, request):
        form = stateform(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/ManageState')
        else:
            # Handle the case where the form data is not valid
            country_records = State.objects.all()
            return render(request, 'state.html', {'form': form, 'country_records': country_records})

class DeleteState(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        data=State.objects.get(id=id)
        data.delete()
        return HttpResponseRedirect('/ManageState')

class managecity(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        city_records=City.objects.all()
        context={
            'city_records':city_records
        }
        return render(request,'adminpages/ManageCity.html',context)
    
class AddCity(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        states=State.objects.all()
        return render(request, 'city.html',{'state_recorsd':states})

    def post(self, request):
        city_name = request.POST.get('name')
        state=request.POST.get('state')
        City.objects.create(name=city_name,state=state)
        return HttpResponseRedirect('/managecity')
    
class DeleteCity(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        data=City.objects.get(id=id)
        data.delete()
        return HttpResponseRedirect('/managecity')



class AddServices(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        return render(request,'adminpages/ServiceCatogry.html')
    def post(self,request):
        Name = request.POST.get('Name')
        Description = request.POST.get('Description')
        img = request.FILES.get('img')
        ServiceCatogarys.objects.create(Name=Name,Description=Description,img=img)

        return HttpResponseRedirect("/ManageServices")



class ManageServices(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        service_records=ServiceCatogarys.objects.all()
        context= {
            'services':service_records,
        }
        return render(request,'adminpages/Manage_Services.html',context)
    

        # form = ServiceCatogoryForm(request.POST,request.FILES)
        # if form.is_valid():
        #     form.save()
        #     return HttpResponse("Ok")
        # else:
        #     return HttpResponse('wrong')

class DeleteServices(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        data = ServiceCatogarys.objects.get(id=id)
        data.delete()

        service_records=ServiceCatogarys.objects.all()
        context= {
            'services':service_records,
        }
        return render(request,'adminpages/Manage_Services.html',context)
    
class EditServices(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request, id):
        service = get_object_or_404(ServiceCatogarys, id=id)
        return render(request,'adminpages/ServiceCatogry.html',{'record':service})
    
    def post(self, request, id):
        service = get_object_or_404(ServiceCatogarys, id=id)
        Name = request.POST.get('Name')
        Description = request.POST.get('Description')
        img = request.FILES.get('img')

        # Update the service category fields
        service.Name = Name
        service.Description = Description
        if img:
            service.img = img
        service.save()
        return HttpResponse("Update Successful")
    
class feedback_form(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    
    def get(self, request):
        worker = workers.objects.all()
        return render(request, 'userpages/feedback_form.html', {'workers': worker})
    
    def post(self, request):
        rating = int(request.POST['rating'])
        description = request.POST['description']
        user = request.user  # Get the currently logged-in user instance
        employ_id = request.POST['employ']
        employ = workers.objects.get(id=employ_id)
        date = datetime.now()

        # Create a new Feedback instance and assign the user, employ, and date
        feedback = Feedback.objects.create(
            Rating=rating, 
            Description=description, 
            User=user, 
            Employ=employ, 
            Date=date
        )
        feedback.save()
        
        # Check if this is an AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Return JSON response with employee details for the popup
            return JsonResponse({
                'success': True,
                'employee_name': f"{employ.admin.first_name} {employ.admin.last_name}",
                'employee_designation': employ.designation,
                'rating': rating,
                'date': date.strftime('%B %d, %Y'),
                'message': 'Your feedback has been submitted successfully!'
            })
        else:
            # For regular form submissions, redirect with a success message
            from django.contrib import messages
            messages.success(request, 'Your feedback has been submitted successfully!')
            return redirect('feedback_form')  # Redirect to the same page

class viewfeedbacks(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        feedback_records=Feedback.objects.all()
        context= {
            'feedback_records':feedback_records,
        }
        return render(request,'adminpages/View_feedbacks.html',context)

class ViewRequests(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        request_records=ServiceRequests.objects.all()
        context={
            'request_records':request_records,
        }
        return render(request, 'adminpages/View_request.html', context)



class ViewColleagues(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        workers_records = workers.objects.all()
        context = {'workers_records': workers_records}
        return render(request, 'workerpages/View_colleagues.html', context)

class WorkerViewRequests(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        worker_id = request.user.id
        worker = workers.objects.get(admin=worker_id)
        
        # Get responses assigned to this worker
        assigned_responses = Response.objects.filter(
            assigned_worker=worker
        )
        
        # Get the corresponding service requests
        request_ids = assigned_responses.values_list('requests', flat=True)
        request_records = ServiceRequests.objects.filter(id__in=request_ids)
        
        context = {
            'request_records': request_records,
            'assigned_responses': assigned_responses,
        }
        return render(request, 'workerpages/View_request.html', context)


class viewworkerfeedbacks(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        # Get the current worker
        worker_id = request.user.id
        worker = workers.objects.get(admin=worker_id)
        
        # Get feedback only for this worker
        feedback_records = Feedback.objects.filter(Employ=worker).order_by('-Date')
        
        # Get sort parameter
        sort_order = request.GET.get('sort', 'newest')
        
        # Apply sorting
        if sort_order == 'oldest':
            feedback_records = feedback_records.order_by('Date')
        elif sort_order == 'highest':
            feedback_records = feedback_records.order_by('-Rating')
        elif sort_order == 'lowest':
            feedback_records = feedback_records.order_by('Rating')
        
        # Calculate average rating and rating distribution
        total_ratings = feedback_records.count()
        if total_ratings > 0:
            average_rating = feedback_records.aggregate(Avg('Rating'))['Rating__avg']
            average_rating_stars = int(average_rating)  # Full stars
            # Determine if we should show a half star (if decimal part is 0.3 or more)
            average_rating_stars_half = average_rating_stars + 1 if average_rating - average_rating_stars >= 0.3 else average_rating_stars
            
            # Calculate rating percentages
            rating_counts = {i: feedback_records.filter(Rating=i).count() for i in range(1, 6)}
            rating_percentages = {i: (count / total_ratings * 100) if total_ratings > 0 else 0 
                                for i, count in rating_counts.items()}
        else:
            average_rating = 0
            average_rating_stars = 0
            average_rating_stars_half = 0
            rating_percentages = {i: 0 for i in range(1, 6)}
        
        # Process each feedback record to ensure proper star display
        for record in feedback_records:
            # Ensure Rating is an integer
            record.Rating = int(record.Rating)
        
        context = {
            'feedback_records': feedback_records,
            'average_rating': average_rating if total_ratings > 0 else 0,
            'average_rating_stars': average_rating_stars,
            'average_rating_stars_half': average_rating_stars_half,
            'rating_percentages': rating_percentages,
        }
        
        return render(request, 'workerpages/View_feedbacks.html', context)


class viewrequests(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        worker=request.user
        print("worker_id",worker)
        request_records=ServiceRequests.objects.all()
        context= {
            'request_records':request_records,
        }
        return render(request,'adminpages/View_request.html',context)
    
class acceptrequest(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request, action, id):
        # Use transaction.atomic to ensure database consistency
        with transaction.atomic():
            # Get the service request and check if it's still available
            request_record = ServiceRequests.objects.select_for_update().get(id=id)
            
            if action == 'accept':
                # Check if this is a specifically chosen request for this worker
                worker = workers.objects.get(admin=request.user.id)
                existing_response = Response.objects.filter(
                    requests=request_record,
                    assigned_worker=worker,
                    worker_specifically_chosen=True
                ).first()
                
                if existing_response:
                    # This is a specifically chosen request for this worker
                    # Mark the request as assigned and update the response status
                    request_record.status = True
                    request_record.save()
                    
                    # Update the scheduled date and time if not already set
                    if not existing_response.scheduled_date:
                        existing_response.scheduled_date = request_record.preferred_date
                    if not existing_response.scheduled_time:
                        existing_response.scheduled_time = request_record.preferred_time
                    existing_response.save()
                    
                    messages.success(request, "You have accepted a request that specifically chose you.")
                elif request_record.status == False:
                    # This is an autofast request that's still available
                    # Mark the request as assigned
                    request_record.status = True
                    request_record.save()
                    
                    # Create a new response record
                    Response.objects.create(
                        requests=request_record,
                        assigned_worker=worker,
                        status=False,  # Not completed yet
                        worker_specifically_chosen=False,  # This was an autofast request
                        scheduled_date=request_record.preferred_date,
                        scheduled_time=request_record.preferred_time
                    )
                    
                    messages.success(request, "You have accepted this service request.")
                else:
                    # The request was already taken by another worker
                    messages.error(request, "This request has already been accepted by another worker.")
                    return HttpResponseRedirect('/AvailableRequests')
                
                return HttpResponseRedirect('/WorkerpendingTask')
            
            else:
                # If the request was already taken by another worker
                if request_record.status == True:
                    messages.error(request, "This request has already been accepted by another worker.")
                return HttpResponseRedirect('/AvailableRequests')
            
class viewresponse(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        Response_records=Response.objects.all()
        context= {
            'Response_records':Response_records,
        }
        return render(request,'adminpages/view_response.html',context)
    
class workerviewresponse(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        worker_id = request.user.id
        # Only get responses that are not completed (status=False)
        assigned_responses = Response.objects.filter(
            assigned_worker__admin__id=worker_id,
            status=False  # This ensures we only get pending tasks
        )
        
        # Get user contact information for each response
        for response in assigned_responses:
            # Add user contact to the response object for template access
            response.user_contact = response.requests.contact
        
        context = {
            'Response_records': assigned_responses,
        }
        return render(request, 'workerpages/viewpending_task.html', context)

class Viewappointment_history(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        # Get the logged-in user's ID
        user_id = request.user.id

        # Query request data for the logged-in user
        requests_data = ServiceRequests.objects.filter(user__admin_id=user_id)

        # Initialize lists to store request and response data
        request_list = []
        assigned_responses = []
        completed_responses = []

        for request_data in requests_data:
            # Check if a response exists for the request
            response = Response.objects.filter(requests=request_data).first()

            if response:
                # Add worker contact information to the response
                worker = response.assigned_worker
                response.worker_contact = worker.contact_number
                
                # Check if the response is completed or still in progress
                if response.status:
                    completed_responses.append(response)
                else:
                    assigned_responses.append(response)
            else:
                # If no response exists, add the request to the request list
                request_list.append(request_data)

        context = {
            'requests': request_list,
            'assigned_responses': assigned_responses,
            'completed_responses': completed_responses,
        }

        return render(request, 'userpages/appointment_history.html', context)
    
class CancelRequest(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        if request.user.is_superuser:
            r_id=ServiceRequests.objects.get(id=id)
            r_id.delete()
            return HttpResponseRedirect('/ViewRequests')
        
        else:
            uid=request.user.id
            # admin=User.object.get(admin=uid)
            user=users.objects.get(admin=uid)
            user_id=user.id
            r_id=ServiceRequests.objects.filter(Q(id=id) & Q(user=user_id))
            r_id.delete()
            return HttpResponseRedirect('/index')


class AssignWorker(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request,id):
        req=ServiceRequests.objects.get(id=id)
        service=req.service.Name
        print(service)

        workers_records=workers.objects.filter(designation=service)
        # print(worker)
        context={
            'req':req,
            'workers_records':workers_records,
        }
        return render(request, 'adminpages/assign_worker.html', context)

    def post(self,request,id):
        ServiceRequests.objects.filter(id=id).update(status=True)
        worker = request.POST.get('assigned_worker')
        req=ServiceRequests.objects.get(id=id)
        print(worker)
        assigned_worker=workers.objects.get(id=worker)
        print(assigned_worker)
        worker_id=workers.objects.get(id=worker) 
        response=Response.objects.create(requests=req,assigned_worker=worker_id,status=False)
        return HttpResponseRedirect('/viewresponse')
        
class userprofile(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self,request):
        id=request.user.id
        data=users.objects.get(admin=id)
        context={
            'data':data,
        }
        return render(request,'userpages/user_profile.html',context)
    
class workerprofile(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        user = request.user.id
        data = workers.objects.get(admin=user)
        
        # Calculate worker statistics
        # 1. Completed requests
        completed_requests = Response.objects.filter(
            assigned_worker=data,
            status=True
        ).count()
        
        # 2. Calculate average rating
        worker_ratings = Feedback.objects.filter(Employ=data)
        if worker_ratings.exists():
            avg_rating = worker_ratings.aggregate(Avg('Rating'))['Rating__avg']
            rating = round(avg_rating, 1)
        else:
            rating = 0.0
        
        # 3. Count unique clients
        client_ids = Response.objects.filter(
            assigned_worker=data
        ).values_list('requests__user', flat=True).distinct()
        total_clients = len(client_ids)
        
        # 4. Count specifically chosen vs autofast assignments
        specific_count = Response.objects.filter(
            assigned_worker=data,
            worker_specifically_chosen=True
        ).count()
        
        autofast_count = Response.objects.filter(
            assigned_worker=data,
            worker_specifically_chosen=False
        ).count()
        
        context = {
            'data': data,
            'completed_requests': completed_requests,
            'rating': rating,
            'total_clients': total_clients,
            'specific_count': specific_count,
            'autofast_count': autofast_count,
        }
        return render(request, 'workerpages/worker_profile.html', context)

class markcompleted(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request, action, id):
        try:
            if action == 'completed':
                # Update the response status to completed
                response = Response.objects.get(id=id, status=False)
                response.status = True
                response.Date = datetime.now()  # Update completion date
                response.save()
                
                messages.success(request, "Task marked as completed successfully.")
                return HttpResponseRedirect('/completed_requests')
            else:
                messages.error(request, "Action not 'completed' or status is already True.")
                return HttpResponseRedirect('/WorkerpendingTask')
                
        except Response.DoesNotExist:
            messages.error(request, "Response not found or already completed.")
            return HttpResponseRedirect('/WorkerpendingTask')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return HttpResponseRedirect('/WorkerpendingTask')

class reject(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request, action, id):
        try:
            with transaction.atomic():
                response_record = Response.objects.get(id=id)
                request_record = response_record.requests
                
                # Mark the service request as unassigned
                request_record.status = False
                request_record.save()
                
                # Delete the response record
                response_record.delete()
                
                messages.success(request, "Request rejected successfully. The job remains open for other workers.")
                return HttpResponseRedirect('/AvailableRequests')
        except Response.DoesNotExist:
            messages.error(request, "Response not found.")
            return HttpResponseRedirect('/WorkerpendingTask')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return HttpResponseRedirect('/WorkerpendingTask')

class AvailableRequests(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    
    def get(self, request):
        # Get the current worker's designation and ID
        worker_id = request.user.id
        worker = workers.objects.get(admin=worker_id)
        worker_designation = worker.designation
        
        # Get filter and sort parameters
        filter_type = request.GET.get('filter', 'all')
        sort_order = request.GET.get('sort', 'newest')
        
        # Get unassigned service requests that match the worker's designation
        regular_requests = ServiceRequests.objects.filter(
            service__Name=worker_designation,
            status=False,
        ).exclude(
            id__in=Response.objects.filter(worker_specifically_chosen=True).values_list('requests_id', flat=True)
        )
        
        # Get specifically assigned requests for this worker that haven't been accepted yet
        specifically_chosen_requests = ServiceRequests.objects.filter(
            service__Name=worker_designation,
            status=False,
            response__assigned_worker=worker,
            response__worker_specifically_chosen=True
        )
        
        # Combine both querysets
        all_available = list(regular_requests)
        
        # Add specifically chosen requests
        for service_request in specifically_chosen_requests:
            if service_request not in all_available:
                all_available.append(service_request)
        
        # Apply filters
        if filter_type == 'specific':
            all_available = [req for req in all_available if 
                Response.objects.filter(
                    requests=req, 
                    assigned_worker=worker,
                    worker_specifically_chosen=True
                ).exists()
            ]
        elif filter_type == 'autofast':
            all_available = [req for req in all_available if not 
                Response.objects.filter(
                    requests=req, 
                    worker_specifically_chosen=True
                ).exists()
            ]
        
        # Apply sorting
        if sort_order == 'oldest':
            all_available.sort(key=lambda x: x.dateofrequest)
        else:
            all_available.sort(key=lambda x: x.dateofrequest, reverse=True)
        
        # Add a flag to each request to indicate if it's specifically chosen for this worker
        for service_request in all_available:
            service_request.is_specifically_chosen = Response.objects.filter(
                requests=service_request,
                assigned_worker=worker,
                worker_specifically_chosen=True
            ).exists()
        
        context = {
            'available_requests': all_available,
            'current_worker_id': worker.id,
        }
        return render(request, 'workerpages/available_requests.html', context)

# ⬇️ Correctly add this OUTSIDE any class (not indented)
def completed_requests(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('login')
        
    # Get the current worker
    worker_id = request.user.id
    worker = workers.objects.get(admin=worker_id)
    
    # Get completed responses for this worker
    completed_responses = Response.objects.filter(
        assigned_worker=worker,
        status=True
    ).select_related(
        'requests', 
        'requests__user', 
        'requests__user__admin',
        'requests__service',
        'requests__city'
    ).order_by('-Date')
    
    # Calculate statistics
    total_completed = completed_responses.count()
    
    # Get filter and sort parameters
    filter_type = request.GET.get('filter', 'all')
    sort_order = request.GET.get('sort', 'newest')
    
    # Apply filters
    if filter_type == 'specific':
        completed_responses = completed_responses.filter(worker_specifically_chosen=True)
    elif filter_type == 'autofast':
        completed_responses = completed_responses.filter(worker_specifically_chosen=False)
    
    # Apply sorting
    if sort_order == 'oldest':
        completed_responses = completed_responses.order_by('Date')
    
    # Enhance each request with additional information
    for response in completed_responses:
        customer = response.requests.user
        response.customer_name = f"{customer.admin.first_name} {customer.admin.last_name}"
        response.customer_email = customer.admin.email
        response.customer_phone = response.requests.contact
        response.customer_address = f"{response.requests.House_No}, {response.requests.Address}, {response.requests.city.name}, {response.requests.pin}"
        response.customer_landmark = response.requests.landmark
        
        response.service_name = response.requests.service.Name
        response.problem_description = response.requests.Problem_Description
        response.requested_date = response.requests.dateofrequest
        response.completed_date = response.Date
        
    context = {
        'completed_requests': completed_responses,
        'total_completed': total_completed,
    }
    
    return render(request, 'workerpages/completed_requests.html', context)

# Add these new view classes to your views.py file

class AllWorkers(View):
    def get(self, request):
        # Get filter parameters
        service_filter = request.GET.get('service', '')
        sort_by = request.GET.get('sort', 'rating')
        
        # Get all verified/active workers
        all_workers = workers.objects.filter(acc_activation=True)
        
        # Apply service filter if specified
        if service_filter:
            service_category = get_object_or_404(ServiceCatogarys, id=service_filter)
            all_workers = all_workers.filter(designation=service_category.Name)
        
        # Group workers by service category
        service_categories = ServiceCatogarys.objects.all()
        workers_by_category = {}
        
        for category in service_categories:
            category_workers = all_workers.filter(designation=category.Name)
            if category_workers.exists():
                workers_by_category[category] = category_workers
        
        # Calculate ratings and other metrics for each worker
        for category, worker_list in workers_by_category.items():
            for worker in worker_list:
                # Get feedback for this worker
                worker_feedback = Feedback.objects.filter(Employ=worker)
                
                # Calculate average rating
                if worker_feedback.exists():
                    avg_rating = worker_feedback.aggregate(Avg('Rating'))['Rating__avg']
                    worker.avg_rating = round(avg_rating, 1)
                    worker.rating_count = worker_feedback.count()
                else:
                    worker.avg_rating = 0
                    worker.rating_count = 0
                
                # Count completed services
                worker.completed_services = Response.objects.filter(
                    assigned_worker=worker,
                    status=True
                ).count()
                
                # Get experience (or default to 0)
                worker.experience_years = worker.experience if hasattr(worker, 'experience') and worker.experience else 0
        
        # Apply sorting within each category
        for category, worker_list in workers_by_category.items():
            if sort_by == 'rating':
                workers_by_category[category] = sorted(worker_list, key=lambda w: w.avg_rating, reverse=True)
            elif sort_by == 'experience':
                workers_by_category[category] = sorted(worker_list, key=lambda w: w.experience_years, reverse=True)
            elif sort_by == 'completed':
                workers_by_category[category] = sorted(worker_list, key=lambda w: w.completed_services, reverse=True)
        
        context = {
            'workers_by_category': workers_by_category,
            'selected_service': service_filter,
            'sort_by': sort_by,
        }
        
        return render(request, 'userpages/all_workers.html', context)
class WorkerPublicProfile(View):
    def get(self, request, id):
        # Get the worker by ID
        worker = get_object_or_404(workers, id=id)
        
        # Get worker's feedback
        feedback_list = Feedback.objects.filter(Employ=worker).order_by('-Date')
        
        # Calculate statistics
        completed_services = Response.objects.filter(
            assigned_worker=worker,
            status=True
        ).count()
        
        # Calculate average rating
        if feedback_list.exists():
            avg_rating = feedback_list.aggregate(Avg('Rating'))['Rating__avg']
            avg_rating = round(avg_rating, 1)
            rating_count = feedback_list.count()
        else:
            avg_rating = 0
            rating_count = 0
        
        # Calculate rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            count = feedback_list.filter(Rating=i).count()
            if rating_count > 0:
                percentage = (count / rating_count) * 100
            else:
                percentage = 0
            rating_distribution[i] = {
                'count': count,
                'percentage': percentage
            }
        
        context = {
            'worker': worker,
            'feedback_list': feedback_list,
            'completed_services': completed_services,
            'avg_rating': avg_rating,
            'rating_count': rating_count,
            'rating_distribution': rating_distribution,
        }
        
        return render(request, 'userpages/worker_profile.html', context)
    










# Admin Profile Views
class adminprofile(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        user = request.user
        try:
            profile = users.objects.get(admin=user)
        except users.DoesNotExist:
            profile = None
        
        context = {
            'user': user,
            'profile': profile,
        }
        return render(request, 'adminpages/adminprofile.html', context)

class admin_settings(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request):
        return redirect('adminprofile')

class update_profile(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def post(self, request):
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        
        user = request.user
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        try:
            profile = users.objects.get(admin=user)
            profile.contact_number = phone
            profile.save()
        except users.DoesNotExist:
            profile = users.objects.create(admin=user, contact_number=phone)
        
        messages.success(request, 'Profile updated successfully')
        return redirect('adminprofile')

class update_address(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def post(self, request):
        address = request.POST.get('address')
        try:
            profile = users.objects.get(admin=request.user)
            profile.Address = address
            profile.save()
        except users.DoesNotExist:
            profile = users.objects.create(admin=request.user, Address=address)
        
        messages.success(request, 'Address updated successfully')
        return redirect('adminprofile')

class change_password(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def post(self, request):
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('adminprofile')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
            return redirect('adminprofile')
        
        user.set_password(new_password)
        user.save()
        
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully')
        return redirect('adminprofile')

class update_profile_pic(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def post(self, request):
        if request.FILES.get('profile_pic'):
            profile_pic = request.FILES['profile_pic']
            try:
                profile = users.objects.get(admin=request.user)
                profile.profile_pic = profile_pic
                profile.save()
            except users.DoesNotExist:
                profile = users.objects.create(admin=request.user, profile_pic=profile_pic)
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

def get_states(request):
    country_id = request.GET.get('country_id')
    states = State.objects.filter(country_id=country_id).values('id', 'name')
    return JsonResponse(list(states), safe=False)

def get_cities(request):
    state_id = request.GET.get('state_id')
    cities = City.objects.filter(state_id=state_id).values('id', 'name')
    return JsonResponse(list(cities), safe=False)

class DeleteWorker(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request, id):
        try:
            # Get the worker object
            worker = workers.objects.get(id=id)
            # Get the associated user account
            user = worker.admin
            # Delete the worker profile first (to avoid foreign key constraints)
            worker.delete()
            # Delete the user account
            user.delete()
            messages.success(request, "Worker deleted successfully!")
        except workers.DoesNotExist:
            messages.error(request, "Worker not found!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        
        return HttpResponseRedirect('/manageworker')

class edit_worker_profile(LoginRequiredMixin, View):
    login_url = '/login/'
    def get(self, request):
        user = request.user.id
        data = workers.objects.get(admin=user)
        context = {
            'data': data,
            'timestamp': int(time.time()),  # Add timestamp to prevent image caching
        }
        return render(request, 'workerpages/worker_profile_edit.html', context)

class update_worker_profile(LoginRequiredMixin, View):
    login_url = '/login/'
    def post(self, request):
        user = request.user
        worker = workers.objects.get(admin=user)
        
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        # Only update email if it's changed and not already in use
        if email != user.email:
            # Check if email is already in use by another user
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Email is already in use by another account.')
                return redirect('edit_worker_profile')
            user.email = email
            user.username = email  # Assuming username is the same as email
        
        user.save()
        
        # Update worker model
        worker.contact_number = contact_number
        worker.Address = address
        worker.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('workerprofile')

class update_worker_profile_pic(LoginRequiredMixin, View):
    login_url = '/login/'
    def post(self, request):
        try:
            if 'profile_pic' in request.FILES:
                profile_pic = request.FILES['profile_pic']
                user = request.user
                worker = workers.objects.get(admin=user)
                
                # Save the profile picture
                worker.profile_pic = profile_pic
                worker.save()
                
                # Return JSON response for AJAX requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                
                messages.success(request, 'Profile picture updated successfully!')
                return redirect('edit_worker_profile')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)
                
                messages.error(request, 'No file uploaded.')
                return redirect('edit_worker_profile')
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('edit_worker_profile')

class change_worker_password(LoginRequiredMixin, View):
    login_url = '/login/'
    def post(self, request):
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Check if current password is correct
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('edit_worker_profile')
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('edit_worker_profile')
        
        # Check password strength (optional)
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('edit_worker_profile')
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Update session to prevent logout
        update_session_auth_hash(request, user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('workerprofile')

def delete_feedback(request, feedback_id):
    if request.user.is_staff or request.user.is_superuser:
        try:
            feedback = Feedback.objects.get(id=feedback_id)
            feedback.delete()
            messages.success(request, "Feedback deleted successfully!")
        except Feedback.DoesNotExist:
            messages.error(request, "Feedback not found!")
    else:
        messages.error(request, "You don't have permission to delete feedback!")
    
    return redirect('viewfeedbacks')  # Redirect to the feedback list page

class DeleteUser(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    def get(self, request, id):
        try:
            user_profile = users.objects.get(id=id)
            user_account = user_profile.admin
            user_profile.delete()
            user_account.delete()
            messages.success(request, "User deleted successfully!")
        except users.DoesNotExist:
            messages.error(request, "User not found!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        
        return HttpResponseRedirect('/manageusers')









class contact(View):
    def get(self, request):
        return render(request, 'userpages/contact.html')

# Add this AJAX endpoint view function after your other view functions
def check_worker_availability_ajax(request):
    """
    AJAX endpoint to check worker availability
    """
    if request.method == 'GET':
        worker_id = request.GET.get('worker_id')
        date_str = request.GET.get('date')
        time_slot = request.GET.get('time_slot')
        
        if not all([worker_id, date_str, time_slot]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        
        try:
            worker = workers.objects.get(id=worker_id)
            is_available = check_worker_availability(worker, date_str, time_slot)
            
            return JsonResponse({
                'worker_id': worker_id,
                'available': is_available
            })
        except workers.DoesNotExist:
            return JsonResponse({'error': 'Worker not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

# Add this class to your views.py file

class WorkerAvailabilityView(LoginRequiredMixin, View):
    login_url = common_lib.DEFAULT_REDIRECT_PATH['ROOT']
    
    def get(self, request):
        # Get the current worker
        worker_id = request.user.id
        worker = workers.objects.get(admin=worker_id)
        
        # Get date range (today + next 14 days)
        today = datetime.now().date()
        date_range = [today + timedelta(days=i) for i in range(15)]
        
        # Get existing availability records
        availability_records = WorkerAvailability.objects.filter(
            worker=worker,
            date__gte=today
        )
        
        # Create a dictionary for easy lookup
        availability_dict = {record.date: record for record in availability_records}
        
        # Prepare data for template
        availability_data = []
        for date in date_range:
            if date in availability_dict:
                record = availability_dict[date]
                availability_data.append({
                    'date': date,
                    'formatted_date': date.strftime('%A, %b %d, %Y'),
                    'morning_available': record.morning_available,
                    'afternoon_available': record.afternoon_available,
                    'evening_available': record.evening_available,
                    'record_exists': True
                })
            else:
                availability_data.append({
                    'date': date,
                    'formatted_date': date.strftime('%A, %b %d, %Y'),
                    'morning_available': True,
                    'afternoon_available': True,
                    'evening_available': True,
                    'record_exists': False
                })
        
        context = {
            'availability_data': availability_data,
            'worker': worker
        }
        
        return render(request, 'workerpages/availability.html', context)
    
    def post(self, request):
        # Get the current worker
        worker_id = request.user.id
        worker = workers.objects.get(admin=worker_id)
        
        # Get form data
        date = request.POST.get('date')
        morning = request.POST.get('morning') == 'on'
        afternoon = request.POST.get('afternoon') == 'on'
        evening = request.POST.get('evening') == 'on'
        
        # Update or create availability record
        WorkerAvailability.objects.update_or_create(
            worker=worker,
            date=date,
            defaults={
                'morning_available': morning,
                'afternoon_available': afternoon,
                'evening_available': evening
            }
        )
        
        messages.success(request, f"Availability for {date} updated successfully.")
        return redirect('worker_availability')
