from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

# Create your models here.


class users(models.Model):
    admin = models.ForeignKey(User, on_delete = models.CASCADE)
    contact_number = models.CharField(max_length=13)
    Address=models.TextField()
    gender = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_pic=models.FileField(upload_to='workers_pic/')

class workers(models.Model):
    admin = models.OneToOneField(User, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=13)
    dob = models.DateField(null=True, blank=True)
    Address = models.TextField()
    city=models.CharField(max_length=255)
    gender = models.CharField(max_length=250)
    designation=models.CharField(max_length=255)
    profile_pic=models.FileField(upload_to='workers_pic/')
    acc_activation=models.BooleanField(default=False)
    avalability_status=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Country(models.Model):
    name = models.CharField(max_length=150)


class State(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)


class City(models.Model):
    state = models.CharField(max_length=150)
    name = models.CharField(max_length=150)

class ServiceCatogarys(models.Model):
    img=models.ImageField(upload_to='catogry_imgs')
    Name=models.CharField(max_length=255)
    Description=models.TextField()
    
class ServiceRequests(models.Model):
    user=models.ForeignKey(users,on_delete=models.CASCADE)
    Problem_Description=models.TextField()
    service = models.ForeignKey(ServiceCatogarys, on_delete=models.CASCADE)
    Address = models.TextField()
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    pin = models.CharField(max_length=10)
    House_No = models.CharField(max_length=20)
    landmark = models.TextField(null=True)
    contact=models.CharField(max_length=200)
    status=models.BooleanField(default=False)
    dateofrequest=models.DateTimeField(auto_now_add=True)
# Add to your models.py file
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=20, choices=[
    ('morning', 'Morning (8:00 AM - 12:00 PM)'),
    ('afternoon', 'Afternoon (12:00 PM - 4:00 PM)'),
    ('evening', 'Evening (4:00 PM - 8:00 PM)')
], null=True, blank=True)


class Feedback(models.Model):
    Rating=models.IntegerField(validators=[MinValueValidator(0),MaxValueValidator(5)])
    Description=models.TextField()
    User=models.ForeignKey(User,on_delete=models.CASCADE)
    # User=models.ForeignKey(users,on_delete=models.CASCADE)
    Employ=models.ForeignKey(workers,on_delete=models.CASCADE)
    Date=models.DateField()


class Profile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    forget_token = models.CharField(max_length=1000)





class Response(models.Model):
    requests = models.ForeignKey(ServiceRequests, on_delete=models.CASCADE)
    assigned_worker = models.ForeignKey(workers, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    Date = models.DateTimeField(auto_now_add=True)
    worker_specifically_chosen = models.BooleanField(default=False)  # Add this field
    # Add to your models.py file
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.CharField(max_length=20, choices=[
    ('morning', 'Morning (8:00 AM - 12:00 PM)'),
    ('afternoon', 'Afternoon (12:00 PM - 4:00 PM)'),
    ('evening', 'Evening (4:00 PM - 8:00 PM)')
    ], null=True, blank=True)
    estimated_hours = models.PositiveIntegerField(null=True, blank=True)
    def __str__(self):
        return f"{self.requests.service.Name} - {self.assigned_worker.admin.username}"





# Add this model to your models.py file if it doesn't exist already

class WorkerAvailability(models.Model):
    worker = models.ForeignKey('workers', on_delete=models.CASCADE)
    date = models.DateField()
    morning_available = models.BooleanField(default=True)
    afternoon_available = models.BooleanField(default=True)
    evening_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('worker', 'date')
        
    def __str__(self):
        return f"{self.worker.admin.username}'s availability on {self.date}"
