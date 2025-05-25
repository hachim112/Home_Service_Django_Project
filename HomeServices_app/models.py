from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

class users(models.Model):
    admin = models.OneToOneField(User, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=13, unique=True)
    Address = models.TextField()
    gender = models.CharField(max_length=10, choices=[
        ('Male', 'Male'),
        ('Female', 'Female')
    ])
    profile_pic = models.ImageField(upload_to='users_pic/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.admin.first_name} {self.admin.last_name}"

class workers(models.Model):
    admin = models.OneToOneField(User, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=13, unique=True)
    dob = models.DateField(null=True, blank=True)
    Address = models.TextField()
    city = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=[
        ('Male', 'Male'),
        ('Female', 'Female')
    ])
    designation = models.CharField(max_length=255)
    profile_pic = models.ImageField(upload_to='workers_pic/', null=True, blank=True)
    acc_activation = models.BooleanField(default=False)
    avalability_status = models.BooleanField(default=True)
    about = models.TextField(null=True, blank=True)
    experience = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.admin.first_name} {self.admin.last_name} - {self.designation}"

class Country(models.Model):
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.country.name}"

class City(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}, {self.state.name}"

class ServiceCatogarys(models.Model):
    img = models.ImageField(upload_to='category_imgs/')
    Name = models.CharField(max_length=255, unique=True)
    Description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Name

class ServiceRequests(models.Model):
    TIME_CHOICES = [
        ('morning', 'Morning (8:00 AM - 12:00 PM)'),
        ('afternoon', 'Afternoon (12:00 PM - 4:00 PM)'),
        ('evening', 'Evening (4:00 PM - 8:00 PM)')
    ]

    user = models.ForeignKey(users, on_delete=models.CASCADE, related_name='service_requests')
    Problem_Description = models.TextField()
    service = models.ForeignKey(ServiceCatogarys, on_delete=models.CASCADE, related_name='requests')
    Address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='service_requests')
    pin = models.CharField(max_length=10)
    House_No = models.CharField(max_length=20)
    landmark = models.TextField(null=True, blank=True)
    contact = models.CharField(max_length=20)
    status = models.BooleanField(default=False)
    dateofrequest = models.DateTimeField(auto_now_add=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=20, choices=TIME_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.service.Name} - {self.user.admin.first_name} {self.user.admin.last_name}"

class Feedback(models.Model):
    Rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    Description = models.TextField()
    User = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks_given')
    Employ = models.ForeignKey(workers, on_delete=models.CASCADE, related_name='feedbacks_received')
    Date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Rating} stars - {self.User.first_name} to {self.Employ.admin.first_name}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    forget_token = models.CharField(max_length=1000, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

class Response(models.Model):
    TIME_CHOICES = [
        ('morning', 'Morning (8:00 AM - 12:00 PM)'),
        ('afternoon', 'Afternoon (12:00 PM - 4:00 PM)'),
        ('evening', 'Evening (4:00 PM - 8:00 PM)')
    ]

    requests = models.ForeignKey(ServiceRequests, on_delete=models.CASCADE, related_name='responses')
    assigned_worker = models.ForeignKey(workers, on_delete=models.CASCADE, related_name='assigned_tasks')
    status = models.BooleanField(default=False)
    Date = models.DateTimeField(auto_now_add=True)
    worker_specifically_chosen = models.BooleanField(default=False)
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.CharField(max_length=20, choices=TIME_CHOICES, null=True, blank=True)

    def __str__(self):
        status_text = "Completed" if self.status else "Pending"
        return f"{self.requests.service.Name} - {self.assigned_worker.admin.first_name} ({status_text})"

class WorkerAvailability(models.Model):
    worker = models.ForeignKey(workers, on_delete=models.CASCADE, related_name='availability_schedule')
    date = models.DateField()
    morning_available = models.BooleanField(default=True)
    afternoon_available = models.BooleanField(default=True)
    evening_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)  # Changed this!
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('worker', 'date')
        
    def __str__(self):
        return f"{self.worker.admin.first_name}'s availability on {self.date}"
