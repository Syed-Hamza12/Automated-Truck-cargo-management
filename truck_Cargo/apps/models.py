from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db import transaction
import logging
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Users (extended)
# ─────────────────────────────────────────
class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER      = 'Owner',      'Owner'
        FLEET_MGR  = 'Fleet Manager', 'Fleet Manager'
        OPS_MGR    = 'Operations Manager', 'Operations Manager'
        DISPATCHER = 'Dispatcher', 'Dispatcher'
        DRIVER     = 'Driver',     'Driver'
        MECHANIC   = 'Mechanic',   'Mechanic'

    role       = models.CharField(max_length=25, choices=Role.choices, default=Role.DRIVER)
    phone      = models.CharField(max_length=30, blank=True)
    avatar     = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='fleet_users',   # ← fixes the clash
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='fleet_users',   # ← fixes the clash
        blank=True,
    )

    class Meta:
        db_table = 'users'


# ─────────────────────────────────────────
# Drivers
# ─────────────────────────────────────────
class Driver(models.Model):
    class LicenseClass(models.TextChoices):
        CLASS_A = 'Class A', 'Class A CDL'
        CLASS_B = 'Class B', 'Class B CDL'
        CLASS_C = 'Class C', 'Class C CDL'

    class Status(models.TextChoices):
        ACTIVE      = 'Active',      'Active'
        OFF_DUTY    = 'Off Duty',    'Off Duty'
        ON_LEAVE    = 'On Leave',    'On Leave'
        SUSPENDED   = 'Suspended',   'Suspended'
        TERMINATED  = 'Terminated',  'Terminated'

    user                = models.OneToOneField(User, on_delete=models.CASCADE,
                                               related_name='driver_profile')
    employee_id         = models.CharField(max_length=50, unique=True)
    license_number      = models.CharField(max_length=50)
    license_class       = models.CharField(max_length=10, choices=LicenseClass.choices)
    license_expiry      = models.DateField()
    medical_cert_expiry = models.DateField(null=True, blank=True)
    hire_date           = models.DateField()
    status              = models.CharField(max_length=15, choices=Status.choices,
                                           default=Status.ACTIVE)
    preferred_shift     = models.CharField(max_length=10,
                                           choices=[('Day', 'Day'), ('Night', 'Night'),
                                                    ('Any', 'Any')],
                                           default='Any',
                                           help_text='Preferred shift for smart dispatching')
    performance_score   = models.DecimalField(max_digits=4, decimal_places=2,
                                              null=True, blank=True,
                                              help_text='AI-calculated performance score 0-100')
    total_miles_driven  = models.PositiveIntegerField(default=0)
    notes               = models.TextField(blank=True)

    class Meta:
        db_table = 'drivers'

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.employee_id})'


# ─────────────────────────────────────────
# Vendors / Service Providers
# ─────────────────────────────────────────
class Vendor(models.Model):
    class VendorType(models.TextChoices):
        MECHANIC       = 'Mechanic',       'Mechanic'
        TIRE_SHOP      = 'Tire Shop',      'Tire Shop'
        PARTS_SUPPLIER = 'Parts Supplier', 'Parts Supplier'
        INSPECTOR      = 'Inspector',      'Inspector'

    vendor_name  = models.CharField(max_length=255)
    vendor_type  = models.CharField(max_length=20, choices=VendorType.choices)
    contact_name = models.CharField(max_length=255, blank=True)
    phone        = models.CharField(max_length=30, blank=True)
    email        = models.EmailField(blank=True)
    address      = models.TextField(blank=True)
    rating       = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
                                       help_text='Internal quality rating 1-5')
    preferred    = models.BooleanField(default=False)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vendors'
        verbose_name = 'Vendor'

    def __str__(self):
        return self.vendor_name


# ─────────────────────────────────────────
# Vendor Invoices
# ─────────────────────────────────────────
class VendorInvoice(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'Pending',  'Pending'
        APPROVED = 'Approved', 'Approved'
        PAID     = 'Paid',     'Paid'
        DISPUTED = 'Disputed', 'Disputed'
        OVERDUE  = 'Overdue',  'Overdue'

    vendor        = models.ForeignKey(Vendor, on_delete=models.CASCADE,
                                      related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True)
    issue_date    = models.DateField()
    due_date      = models.DateField()
    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    status        = models.CharField(max_length=10, choices=Status.choices,
                                     default=Status.PENDING)
    paid_date     = models.DateField(null=True, blank=True)
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vendor_invoices'

    def __str__(self):
        return f'Invoice {self.invoice_number} – {self.vendor}'


# ─────────────────────────────────────────
# Trucks
# ─────────────────────────────────────────


class fleet_department(models.Model):
    location = models.CharField(max_length=100)
    department_name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fleet_departments')

    def __str__(self):
        return self.department_name
class dispatch_department(models.Model):
    location = models.CharField(max_length=100)
    department_name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dispatch_departments')
    def __str__(self):
        return self.department_name

class Truck(models.Model):
    class Status(models.TextChoices):
        ACTIVE         = 'Active',         'Active'
        IN_MAINTENANCE = 'In Maintenance', 'In Maintenance'
        OUT_OF_SERVICE = 'Out of Service', 'Out of Service'
        RETIRED        = 'Retired',        'Retired'

    
    unit_number        = models.CharField(max_length=50, unique=True,
                                          help_text='Internal fleet identifier e.g. TRK-001')
    dispatcher_department = models.ForeignKey(
        dispatch_department, 
        on_delete=models.SET_NULL,  # Keeps the truck if a department is deleted
        related_name='trucks', 
        null=True, 
        blank=True
    )
    
    fleet_department = models.ForeignKey(
        fleet_department, 
        on_delete=models.SET_NULL, 
        related_name='trucks', 
        null=True, 
        blank=True
    )
    make               = models.CharField(max_length=100)
    model              = models.CharField(max_length=100)
    year               = models.PositiveIntegerField()
    vin                = models.CharField(max_length=17, unique=True)
    license_plate      = models.CharField(max_length=20)
    status             = models.CharField(max_length=20, choices=Status.choices,
                                          default=Status.ACTIVE)
    assigned_driver    = models.ForeignKey(Driver, null=True, blank=True,
                                           on_delete=models.SET_NULL,
                                           related_name='assigned_trucks')
    current_mileage    = models.PositiveIntegerField(default=0)
    purchase_date      = models.DateField(null=True, blank=True)
    purchase_cost      = models.DecimalField(max_digits=12, decimal_places=2,
                                             null=True, blank=True)
    dot_inspection_expiry = models.DateField(null=True, blank=True,
                                             help_text='Annual DOT inspection expiry date')
    notes              = models.TextField(blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trucks'
        verbose_name = 'Truck'

    def __str__(self):
        return f'{self.unit_number} ({self.make} {self.model} {self.year})'


# ─────────────────────────────────────────
# Truck Locations (GPS / Live Tracking)
# ─────────────────────────────────────────
class TruckLocation(models.Model):
    truck      = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                   related_name='locations')
    latitude   = models.DecimalField(max_digits=9, decimal_places=6)
    longitude  = models.DecimalField(max_digits=9, decimal_places=6)
    speed_mph  = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    heading    = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                     help_text='Degrees 0-360')
    odometer   = models.PositiveIntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'truck_locations'
        ordering = ['-recorded_at']

    def __str__(self):
        return f'{self.truck} @ {self.recorded_at}'




# ─────────────────────────────────────────
# Loads
# ─────────────────────────────────────────
class Load(models.Model):
    class Status(models.TextChoices):
        Active    = 'Active',    'Active'
        DELIVERED  = 'Delivered',  'Delivered'
        CANCELLED  = 'Cancelled',  'Cancelled'

    load_number      = models.CharField(max_length=100, unique=True)
    customer_name    = models.CharField(max_length=255, blank=True)
    origin           = models.CharField(max_length=255)
    pickup_contact_phone = models.CharField(max_length=30, blank=True)

    destination_latitude  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination      = models.CharField(max_length=255)
    delivery_contact_phone = models.CharField(max_length=30, blank=True)
    pickup_date      = models.DateTimeField()
    delivery_date    = models.DateTimeField(null=True, blank=True)
    weight_lbs       = models.DecimalField(max_digits=10, decimal_places=2,
                                           null=True, blank=True)
    commodity        = models.CharField(max_length=255, blank=True)
    rate             = models.DecimalField(max_digits=10, decimal_places=2,
                                           null=True, blank=True,
                                           help_text='Revenue for this load')
    status           = models.CharField(max_length=15, choices=Status.choices,
                                        default=Status.Active)
    created_by       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                         related_name='created_loads')
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    dispatcher_department = models.ForeignKey(
        dispatch_department, 
        on_delete=models.SET_NULL,  # Keeps the truck if a department is deleted
        related_name='load_department', 
        null=True, 
        blank=True
    )

    class Meta:
        db_table = 'loads'

    def __str__(self):
        return f'Load {self.load_number} ({self.origin} → {self.destination})'

# ------------------------------------------
# Pakages
# ------------------------------------------

class Package(models.Model):

    class Status(models.TextChoices):
        RECEIVED = "Received"
        LOADED = "Loaded"
        IN_TRANSIT = "In Transit"
        DELIVERED = "Delivered"

    tracking_number = models.CharField(
        max_length=100,
        unique=True
    )

    sender_name = models.CharField(
        max_length=255
    )

    sender_phone = models.CharField(
        max_length=20
    )

    receiver_name = models.CharField(
        max_length=255
    )

    receiver_phone = models.CharField(
        max_length=20
    )

    origin = models.CharField(
        max_length=255
    )

    destination = models.CharField(
        max_length=255
    )

    weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    load = models.ForeignKey(
    Load,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="packages"
    )
    dispatcher_department = models.ForeignKey(
        dispatch_department, 
        on_delete=models.SET_NULL,  # Keeps the truck if a department is deleted
        related_name='packages_department', 
        null=True, 
        blank=True
    )


# ─────────────────────────────────────────
# Load Assignments
# ────────────────────────────────────────

class LoadAssignment(models.Model):
    load       = models.ForeignKey(Load, on_delete=models.CASCADE,
                                   related_name='assignments')
    truck      = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                   related_name='load_assignments')
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE,
                                   related_name='load_assignments')
    assigned_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                    related_name='dispatched_loads')
    assigned_at = models.DateTimeField(default=timezone.now)
    is_active   = models.BooleanField(default=True)
    notes       = models.TextField(blank=True)
    dispatcher_department = models.ForeignKey(
        dispatch_department, 
        on_delete=models.SET_NULL,  # Keeps the truck if a department is deleted
        related_name='laod_assignment_department', 
        null=True, 
        blank=True
    )

    class Meta:
        db_table = 'load_assignments'

    def __str__(self):
        return f'{self.load} → {self.truck} / {self.driver}'
    



# ─────────────────────────────────────────
# Trips
# ─────────────────────────────────────────
class Trip(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = 'Active',    'Active'
        COMPLETED  = 'Completed',  'Completed'
        CANCELLED  = 'Cancelled',  'Cancelled'

    loads = models.ManyToManyField(
    Load,
    related_name="trips",
    blank=True
    )
    truck           = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                        related_name='trips')
    driver          = models.ForeignKey(Driver, on_delete=models.CASCADE,
                                        related_name='trips')
    start_datetime  = models.DateTimeField(null=True, blank=True)
    end_datetime    = models.DateTimeField(null=True, blank=True)
    start_mileage   = models.PositiveIntegerField(null=True, blank=True)
    end_mileage     = models.PositiveIntegerField(null=True, blank=True)
    distance_miles  = models.DecimalField(max_digits=8, decimal_places=2,
                                          null=True, blank=True,
                                          help_text='Auto-calculated from mileage delta')
    fuel_used_gal   = models.DecimalField(max_digits=7, decimal_places=3,
                                          null=True, blank=True)
    assigned_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                    related_name='dispatched_trips')
    complete_approve = models.BooleanField(default=False)
    status          = models.CharField(max_length=15, choices=Status.choices,
                                       default=Status.PLANNED)
    delay_reason    = models.TextField(blank=True,
                                       help_text='If late, record reason for driver performance')
    dispatcher_department = models.ForeignKey(
        dispatch_department, 
        on_delete=models.SET_NULL,  # Keeps the truck if a department is deleted
        related_name='trip_department', 
        null=True, 
        blank=True
    )

    class Meta:
        db_table = 'trips'

    def save(self, *args, **kwargs):
        # 1. Calculate mileage delta
        if self.start_mileage and self.end_mileage:
            self.distance_miles = self.end_mileage - self.start_mileage
        
        is_new = self.pk is None
        is_cancelled = False
        is_completed = False
        is_just_approved = False

        # 2. Check if the status was changed to CANCELLED
        if not is_new:
            try:
                original = Trip.objects.get(pk=self.pk)
                
                if original.status != self.Status.CANCELLED and self.status == self.Status.CANCELLED:
                    is_cancelled = True
                elif original.status != self.Status.COMPLETED and self.status == self.Status.COMPLETED:
                    is_completed = True
                
                # Check if complete_approve changed from False to True
                if not original.complete_approve and self.complete_approve:
                    is_just_approved = True
            except Trip.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if is_just_approved:
            try:
                lat = getattr(self.load, 'destination_latitude', None)
                lng = getattr(self.load, 'destination_longitude', None)
                destination = getattr(self.load, 'destination', None)
                TripEvent.objects.create(
                    trip=self,
                    event_type=TripEvent.EventType.DELIVERY,
                    latitude=lat, 
                    longitude=lng,
                    destination=destination,
                    description="Trip completion approved by dispatcher.",
                    recorded_by=self.assigned_by,  # Attributes event log to the assigning dispatcher
                    recorded_at=timezone.now()
                )
            except Exception as e:
                logger.error(f"Failed to create TripEvent log for trip {self.id}: {e}", exc_info=True)

        # Helper function to broadcast message safely after DB commit
        def send_notification(channel_group, event_type):
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                channel_group,
                {
                    "type": "send_notification",
                    "value": {
                        "event": event_type,  # Dynamically sets 'trip' or 'trip_cancelled'
                        "trip_id": self.id
                    }
                }
            )

        # 3. Trigger events post-commit
        if is_new:
            driver_group = f"user_{self.driver.user.id}"
            transaction.on_commit(lambda: send_notification(driver_group, "Added"))
        elif is_cancelled:
            driver_group = f"user_{self.driver.user.id}"
            transaction.on_commit(lambda: send_notification(driver_group, "trip_cancelled"))
        elif is_completed and self.assigned_by:
            assigner_group = f"user_{self.assigned_by.id}"
            transaction.on_commit(lambda: send_notification(assigner_group, "trip_completed"))

    def __str__(self):
        return f'Trip for {self.load} – {self.status}'


# ─────────────────────────────────────────
# Trip Events (breadcrumb / log)
# ─────────────────────────────────────────
class TripEvent(models.Model):
    class EventType(models.TextChoices):
        DEPARTURE   = 'Departure',   'Departure'
        STOP        = 'Stop',        'Stop'
        DELAY       = 'Delay',       'Delay'
        INCIDENT    = 'Incident',    'Incident'
        DELIVERY    = 'Delivery',    'Delivery'
        ARRIVAL     = 'Arrival',     'Arrival'

    trip        = models.ForeignKey(Trip, on_delete=models.CASCADE,
                                    related_name='events')
    event_type  = models.CharField(max_length=15, choices=EventType.choices)
    latitude    = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                    related_name='trip_events')

    class Meta:
        db_table = 'trip_events'
        ordering = ['recorded_at']

    def __str__(self):
        return f'{self.trip} – {self.event_type} @ {self.recorded_at}'


# ─────────────────────────────────────────
# Maintenance History
# ─────────────────────────────────────────
class MaintenanceHistory(models.Model):
    class MaintenanceType(models.TextChoices):
        PM         = 'PM',         'Preventive Maintenance'
        REPAIR     = 'Repair',     'Repair'
        INSPECTION = 'Inspection', 'Inspection'
        TIRE       = 'Tire',       'Tire'
        OTHER      = 'Other',      'Other'

    class Status(models.TextChoices):
        COMPLETED   = 'Completed',   'Completed'
        IN_PROGRESS = 'In Progress', 'In Progress'
        PENDING     = 'Pending',     'Pending'

    truck              = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                           related_name='maintenance_history')
    maintenance_type   = models.CharField(max_length=20, choices=MaintenanceType.choices)
    date_performed     = models.DateField()
    mileage_at_service = models.PositiveIntegerField()
    performed_by       = models.CharField(max_length=255)
    vendor             = models.ForeignKey(Vendor, null=True, blank=True,
                                           on_delete=models.SET_NULL,
                                           related_name='maintenance_records')
    description        = models.TextField(blank=True)
    total_cost         = models.DecimalField(max_digits=10, decimal_places=2,
                                             null=True, blank=True)
    downtime_hours     = models.DecimalField(max_digits=6, decimal_places=2,
                                             null=True, blank=True)
    status             = models.CharField(max_length=15, choices=Status.choices,
                                          default=Status.PENDING)
    created_by         = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                           related_name='maintenance_logs')
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'maintenance_history'
        verbose_name = 'Maintenance History'
        ordering = ['-date_performed']

    def __str__(self):
        return f'{self.truck} – {self.maintenance_type} on {self.date_performed}'


# ─────────────────────────────────────────
# Preventive Maintenance Schedule
# ─────────────────────────────────────────
class PreventiveMaintenance(models.Model):
    class Status(models.TextChoices):
        ON_SCHEDULE = 'On Schedule', 'On Schedule'
        DUE_SOON    = 'Due Soon',    'Due Soon'
        OVERDUE     = 'Overdue',     'Overdue'

    truck                  = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                               related_name='pm_schedules')
    pm_type                = models.CharField(max_length=100,
                                              help_text='e.g. Oil Change, Tire Rotation, DOT Inspection')
    interval_miles         = models.PositiveIntegerField(null=True, blank=True)
    interval_days          = models.PositiveIntegerField(null=True, blank=True)
    last_performed_date    = models.DateField(null=True, blank=True)
    last_performed_mileage = models.PositiveIntegerField(null=True, blank=True)
    next_due_date          = models.DateField(null=True, blank=True)
    next_due_mileage       = models.PositiveIntegerField(null=True, blank=True)
    status                 = models.CharField(max_length=15, choices=Status.choices,
                                              default=Status.ON_SCHEDULE)
    notes                  = models.TextField(blank=True)

    class Meta:
        db_table = 'preventive_maintenance'
        verbose_name = 'Preventive Maintenance'

    def __str__(self):
        return f'{self.truck} – {self.pm_type} (next: {self.next_due_date})'

    def save(self, *args, **kwargs):
        if self.last_performed_date and self.interval_days:
            self.next_due_date = self.last_performed_date + timedelta(days=self.interval_days)
        if self.last_performed_mileage and self.interval_miles:
            self.next_due_mileage = self.last_performed_mileage + self.interval_miles
        super().save(*args, **kwargs)


# ─────────────────────────────────────────
# Repair Orders (replaces old Repair model)
# ─────────────────────────────────────────
class RepairOrder(models.Model):
    class ReportedBy(models.TextChoices):
        DRIVER     = 'Driver',     'Driver'
        DISPATCHER = 'Dispatcher', 'Dispatcher'
        INSPECTOR  = 'Inspector',  'Inspector'

    class Priority(models.TextChoices):
        CRITICAL = 'Critical', 'Critical'
        HIGH     = 'High',     'High'
        NORMAL   = 'Normal',   'Normal'
        LOW      = 'Low',      'Low'

    class Status(models.TextChoices):
        REPORTED  = 'Reported',  'Reported'
        APPROVED  = 'Approved',  'Approved'
        IN_REPAIR = 'In Repair', 'In Repair'
        COMPLETED = 'Completed', 'Completed'
        CLOSED    = 'Closed',    'Closed'

    truck             = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                          related_name='repair_orders')
    reported_by       = models.CharField(max_length=15, choices=ReportedBy.choices)
    reported_date     = models.DateTimeField(default=timezone.now)
    issue_description = models.TextField()
    priority          = models.CharField(max_length=10, choices=Priority.choices,
                                         default=Priority.NORMAL)
    approved_by       = models.ForeignKey(User, null=True, blank=True,
                                          on_delete=models.SET_NULL,
                                          related_name='approved_repairs')
    approval_date     = models.DateTimeField(null=True, blank=True)
    vendor            = models.ForeignKey(Vendor, null=True, blank=True,
                                          on_delete=models.SET_NULL,
                                          related_name='repair_orders')
    estimated_cost    = models.DecimalField(max_digits=10, decimal_places=2,
                                            null=True, blank=True)
    actual_cost       = models.DecimalField(max_digits=10, decimal_places=2,
                                            null=True, blank=True)
    repair_start      = models.DateTimeField(null=True, blank=True)
    repair_complete   = models.DateTimeField(null=True, blank=True)
    status            = models.CharField(max_length=15, choices=Status.choices,
                                         default=Status.REPORTED)
    root_cause        = models.TextField(blank=True)

    class Meta:
        db_table = 'repair_orders'
        verbose_name = 'Repair Order'
        ordering = ['-reported_date']

    def __str__(self):
        return f'{self.truck} – {self.priority} repair ({self.status})'


# ─────────────────────────────────────────
# Downtime Tracking
# ─────────────────────────────────────────
class Downtime(models.Model):
    class Reason(models.TextChoices):
        BREAKDOWN    = 'Breakdown',    'Breakdown'
        PM           = 'PM',           'Preventive Maintenance'
        INSPECTION   = 'Inspection',   'Inspection'
        ACCIDENT     = 'Accident',     'Accident'
        DRIVER_FAULT = 'Driver Fault', 'Driver Fault'

    truck            = models.ForeignKey(Truck, on_delete=models.CASCADE,
                                         related_name='downtimes')
    repair_order     = models.ForeignKey(RepairOrder, null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         related_name='downtime_records')
    reason           = models.CharField(max_length=20, choices=Reason.choices)
    start_datetime   = models.DateTimeField()
    end_datetime     = models.DateTimeField(null=True, blank=True)
    total_hours      = models.DecimalField(max_digits=8, decimal_places=2,
                                           null=True, blank=True)
    revenue_lost_est = models.DecimalField(max_digits=12, decimal_places=2,
                                           null=True, blank=True)
    notes            = models.TextField(blank=True)

    class Meta:
        db_table = 'downtime'
        ordering = ['-start_datetime']

    def save(self, *args, **kwargs):
        if self.start_datetime and self.end_datetime:
            delta = self.end_datetime - self.start_datetime
            self.total_hours = round(delta.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.truck} – {self.reason} from {self.start_datetime}'


# ─────────────────────────────────────────
# Parts Inventory
# ─────────────────────────────────────────
class Inventory(models.Model):
    part_name           = models.CharField(max_length=255)
    part_number         = models.CharField(max_length=100, unique=True)
    category            = models.CharField(max_length=100,
                                           help_text='e.g. Engine, Brakes, Tires, Electrical')
    quantity_on_hand    = models.PositiveIntegerField(default=0)
    reorder_level       = models.PositiveIntegerField(default=0)
    unit_cost           = models.DecimalField(max_digits=10, decimal_places=2)
    supplier            = models.ForeignKey(Vendor, null=True, blank=True,
                                            on_delete=models.SET_NULL,
                                            related_name='supplied_parts')
    location            = models.CharField(max_length=100, blank=True,
                                           help_text='Shelf/bin location')
    last_restocked_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'inventory'
        verbose_name = 'Inventory'

    def __str__(self):
        return f'{self.part_name} ({self.part_number})'

    @property
    def needs_reorder(self):
        return self.quantity_on_hand <= self.reorder_level


# ─────────────────────────────────────────
# Inventory Transactions
# ─────────────────────────────────────────
class InventoryTransaction(models.Model):
    class TransactionType(models.TextChoices):
        RESTOCK  = 'Restock',  'Restock'
        USED     = 'Used',     'Used in Repair/PM'
        ADJUST   = 'Adjust',   'Manual Adjustment'
        RETURNED = 'Returned', 'Returned'

    part          = models.ForeignKey(Inventory, on_delete=models.CASCADE,
                                      related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity      = models.IntegerField(help_text='Positive for in, negative for out')
    unit_cost     = models.DecimalField(max_digits=10, decimal_places=2,
                                        null=True, blank=True)
    repair_order  = models.ForeignKey(RepairOrder, null=True, blank=True,
                                      on_delete=models.SET_NULL,
                                      related_name='parts_used')
    maintenance   = models.ForeignKey(MaintenanceHistory, null=True, blank=True,
                                      on_delete=models.SET_NULL,
                                      related_name='parts_used')
    performed_by  = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                      related_name='inventory_transactions')
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_transactions'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep quantity_on_hand in sync
        self.part.quantity_on_hand = max(
            0, self.part.quantity_on_hand + self.quantity
        )
        self.part.save(update_fields=['quantity_on_hand'])

    def __str__(self):
        return f'{self.transaction_type} {self.quantity}x {self.part} @ {self.created_at}'


# ─────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────
class Alert(models.Model):
    class AlertType(models.TextChoices):
        PM_DUE_SOON        = 'PM Due Soon',         'PM Due Soon'
        PM_OVERDUE         = 'PM Overdue',           'PM Overdue'
        TRUCK_OUT_SERVICE  = 'Truck Out of Service', 'Truck Out of Service'
        TRUCK_INSPECTION_REQUIRE = 'Truck Inspection Required', 'Truck Inspection Required'
        REPAIR_NOT_APPROVED = 'Repair Not Approved', 'Repair Not Approved (24h)'
        REPEATED_REPAIR    = 'Repeated Repair',      'Repeated Repair (3x in 90 days)'
        HIGH_MAINT_COST    = 'High Maintenance Cost','High Maintenance Cost'
        LONG_DOWNTIME      = 'Long Downtime',        'Long Downtime (48h+)'
        PARTS_REORDER      = 'Parts Reorder',        'Parts Reorder Needed'
        INVOICE_DUE        = 'Invoice Due',           'Vendor Invoice Due'
        DOT_INSPECTION_DUE = 'DOT Inspection Due',   'Annual DOT Inspection Due'

    class Priority(models.TextChoices):
        CRITICAL = 'Critical', 'Critical'
        HIGH     = 'High',     'High'
        MEDIUM   = 'Medium',   'Medium'
        LOW      = 'Low',      'Low'

    alert_type   = models.CharField(max_length=25, choices=AlertType.choices)
    priority     = models.CharField(max_length=10, choices=Priority.choices)
    truck        = models.ForeignKey(Truck, null=True, blank=True,
                                     on_delete=models.CASCADE, related_name='alerts')
    repair_order = models.ForeignKey(RepairOrder, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='alerts')
    part         = models.ForeignKey(Inventory, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='alerts')
    message      = models.TextField()
    is_resolved  = models.BooleanField(default=False)
    resolved_at  = models.DateTimeField(null=True, blank=True)
    resolved_by  = models.ForeignKey(User, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='resolved_alerts')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.priority}] {self.alert_type} – {self.created_at.date()}'


# ─────────────────────────────────────────
# Notifications (delivery log per user)
# ─────────────────────────────────────────
class Notification(models.Model):
    class Channel(models.TextChoices):
        IN_APP = 'In-App', 'In-App'
        EMAIL  = 'Email',  'Email'
        SMS    = 'SMS',    'SMS'
        LOAD_ASSIGNED = 'Load Assigned', 'Load Assigned to Driver'

    alert    = models.ForeignKey(Alert, on_delete=models.CASCADE,
                                 related_name='notifications')
    user     = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name='notifications')
    channel  = models.CharField(max_length=20, choices=Channel.choices,
                                default=Channel.IN_APP)
    is_read  = models.BooleanField(default=False)
    read_at  = models.DateTimeField(null=True, blank=True)
    sent_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-sent_at']

    def __str__(self):
        return f'Notification → {self.user} via {self.channel}'
    

class IssueReport(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE)

    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)


# ─────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────
class AuditLog(models.Model):
    user         = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                     related_name='audit_logs')
    action       = models.CharField(max_length=50,
                                    help_text='e.g. CREATE, UPDATE, DELETE, LOGIN')
    table_name   = models.CharField(max_length=100)
    record_id    = models.PositiveIntegerField(null=True, blank=True)
    old_data     = models.JSONField(null=True, blank=True,
                                    help_text='Snapshot before change')
    new_data     = models.JSONField(null=True, blank=True,
                                    help_text='Snapshot after change')
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} – {self.action} on {self.table_name}#{self.record_id}'


# ─────────────────────────────────────────
# AI Conversations
# ─────────────────────────────────────────
class AIConversation(models.Model):
    user       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,
                                   related_name='ai_conversations')
    session_id = models.CharField(max_length=100, unique=True)
    title      = models.CharField(max_length=255, blank=True,
                                   help_text='Auto-generated or user-set conversation title')
    context    = models.JSONField(default=dict,
                                  help_text='Relevant fleet context supplied to the AI')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_conversations'
        ordering = ['-started_at']

    def __str__(self):
        return f'AI Session {self.session_id} by {self.user}'


class AIMessage(models.Model):
    class Role(models.TextChoices):
        USER      = 'user',      'User'
        ASSISTANT = 'assistant', 'Assistant'

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE,
                                     related_name='messages')
    role         = models.CharField(max_length=10, choices=Role.choices)
    content      = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_messages'
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] in {self.conversation.session_id}'


# ─────────────────────────────────────────
# AI Actions (actions triggered by AI assistant)
# ─────────────────────────────────────────
class AIAction(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'Pending',   'Pending'
        APPROVED  = 'Approved',  'Approved'
        EXECUTED  = 'Executed',  'Executed'
        REJECTED  = 'Rejected',  'Rejected'

    conversation  = models.ForeignKey(AIConversation, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='actions')
    action_type   = models.CharField(max_length=100,
                                     help_text='e.g. CreateRepairOrder, SendAlert, UpdatePMStatus')
    payload       = models.JSONField(help_text='Parameters for the action')
    status        = models.CharField(max_length=10, choices=Status.choices,
                                     default=Status.PENDING)
    approved_by   = models.ForeignKey(User, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='approved_ai_actions')
    executed_at   = models.DateTimeField(null=True, blank=True)
    result        = models.JSONField(null=True, blank=True,
                                     help_text='Outcome / response after execution')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_actions'
        ordering = ['-created_at']

    def __str__(self):
        return f'AI Action: {self.action_type} ({self.status})'


# ─────────────────────────────────────────
# ML Predictions
# ─────────────────────────────────────────
class MLPrediction(models.Model):
    class PredictionType(models.TextChoices):
        DOWNTIME_FORECAST  = 'Downtime Forecast',   'Next Downtime Forecast'
        MAINTENANCE_NEEDED = 'Maintenance Needed',   'Maintenance Needed Soon'
        COST_ANOMALY       = 'Cost Anomaly',          'Unusual Cost Spike'
        DRIVER_PERFORMANCE = 'Driver Performance',   'Driver Performance Score'
        LOAD_EFFICIENCY    = 'Load Efficiency',       'Load/Route Efficiency'

    truck           = models.ForeignKey(Truck, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='ml_predictions')
    driver          = models.ForeignKey(Driver, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='ml_predictions')
    prediction_type = models.CharField(max_length=25, choices=PredictionType.choices)
    predicted_value = models.JSONField(help_text='Prediction payload — date, score, flag, etc.')
    confidence      = models.DecimalField(max_digits=5, decimal_places=2,
                                          null=True, blank=True,
                                          help_text='Confidence score 0-100')
    model_version   = models.CharField(max_length=50, blank=True,
                                       help_text='Version of ML model that generated this')
    is_actioned     = models.BooleanField(default=False,
                                          help_text='Fleet manager acknowledged this prediction')
    generated_at    = models.DateTimeField(auto_now_add=True)
    valid_until     = models.DateTimeField(null=True, blank=True,
                                           help_text='Expiry of this prediction')

    class Meta:
        db_table = 'ml_predictions'
        ordering = ['-generated_at']

    def __str__(self):
        target = self.truck or self.driver
        return f'ML [{self.prediction_type}] for {target} @ {self.generated_at.date()}'

