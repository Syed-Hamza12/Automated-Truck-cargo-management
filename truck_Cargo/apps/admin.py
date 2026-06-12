from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, Driver, Vendor, VendorInvoice,
    Truck, TruckLocation,
    Load, LoadAssignment, Trip, TripEvent,
    MaintenanceHistory, PreventiveMaintenance, RepairOrder, Downtime,
    Inventory, InventoryTransaction,
    Alert, Notification,
    AuditLog,
    AIConversation, AIMessage, AIAction,
    MLPrediction,
    LoadNotification
)


# ─────────────────────────────────────────
# Users
# ─────────────────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('username', 'get_full_name', 'email', 'role', 'phone', 'is_active')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering      = ('username',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Fleet Info', {'fields': ('role', 'phone', 'avatar')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Fleet Info', {'fields': ('role', 'phone')}),
    )


# ─────────────────────────────────────────
# Drivers
# ─────────────────────────────────────────
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('employee_id', 'get_full_name', 'license_class', 'license_expiry',
                     'status', 'preferred_shift', 'performance_score')
    list_filter   = ('status', 'license_class', 'preferred_shift')
    search_fields = ('employee_id', 'user__first_name', 'user__last_name', 'license_number')
    ordering      = ('employee_id',)
    readonly_fields = ('performance_score', 'total_miles_driven')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'


# ─────────────────────────────────────────
# Vendors
# ─────────────────────────────────────────
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display  = ('vendor_name', 'vendor_type', 'contact_name', 'phone', 'rating', 'preferred')
    list_filter   = ('vendor_type', 'preferred')
    search_fields = ('vendor_name', 'contact_name', 'email')
    ordering      = ('vendor_name',)


@admin.register(VendorInvoice)
class VendorInvoiceAdmin(admin.ModelAdmin):
    list_display  = ('invoice_number', 'vendor', 'amount', 'issue_date', 'due_date', 'status')
    list_filter   = ('status',)
    search_fields = ('invoice_number', 'vendor__vendor_name')
    ordering      = ('-issue_date',)
    date_hierarchy = 'issue_date'


# ─────────────────────────────────────────
# Trucks
# ─────────────────────────────────────────
@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display  = ('unit_number', 'make', 'model', 'year', 'status',
                     'assigned_driver', 'current_mileage', 'dot_inspection_expiry')
    list_filter   = ('status', 'make', 'year')
    search_fields = ('unit_number', 'vin', 'license_plate', 'make', 'model')
    ordering      = ('unit_number',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TruckLocation)
class TruckLocationAdmin(admin.ModelAdmin):
    list_display  = ('truck', 'latitude', 'longitude', 'speed_mph', 'recorded_at')
    list_filter   = ('truck',)
    search_fields = ('truck__unit_number',)
    ordering      = ('-recorded_at',)
    date_hierarchy = 'recorded_at'
    readonly_fields = ('recorded_at',)


# ─────────────────────────────────────────
# Loads & Assignments
# ─────────────────────────────────────────
class LoadAssignmentInline(admin.TabularInline):
    model  = LoadAssignment
    extra  = 0
    fields = ('truck', 'driver', 'assigned_by', 'assigned_at', 'is_active')
    readonly_fields = ('assigned_at',)


@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display  = ('load_number', 'customer_name', 'origin', 'destination',
                     'pickup_date', 'status', 'rate')
    list_filter   = ('status',)
    search_fields = ('load_number', 'customer_name', 'origin', 'destination')
    ordering      = ('-pickup_date',)
    date_hierarchy = 'pickup_date'
    inlines       = [LoadAssignmentInline]

class LoadNotificationInline(admin.TabularInline):
    model       = LoadNotification
    extra       = 0
    fields      = ('channel', 'status', 'whatsapp_number', 'sent_at', 'delivered_at', 'read_at','is_read')
    readonly_fields = ('sent_at', 'delivered_at', 'read_at', 'created_at' ,)

@admin.register(LoadNotification)
class LoadNotificationAdmin(admin.ModelAdmin):
    list_display  = ('driver', 'assignment', 'channel', 'status', 'whatsapp_number', 'sent_at' , 'read_at' , 'is_read')
    list_filter   = ('channel', 'status')
    search_fields = ('driver__user__first_name', 'driver__employee_id', 'whatsapp_number')
    ordering      = ('-created_at',)
    readonly_fields = ('sent_at', 'delivered_at', 'read_at', 'created_at' ,)

@admin.register(LoadAssignment)
class LoadAssignmentAdmin(admin.ModelAdmin):
    list_display  = ('load', 'truck', 'driver', 'assigned_by', 'assigned_at', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('load__load_number', 'truck__unit_number', 'driver__employee_id')
    ordering      = ('-assigned_at',)
    inlines = [LoadNotificationInline]


# ─────────────────────────────────────────
# Trips
# ─────────────────────────────────────────
class TripEventInline(admin.TabularInline):
    model  = TripEvent
    extra  = 0
    fields = ('event_type', 'description', 'recorded_at', 'recorded_by')
    readonly_fields = ('recorded_at',)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = ('id', 'load', 'truck', 'driver', 'status',
                     'start_datetime', 'end_datetime', 'distance_miles')
    list_filter   = ('status',)
    search_fields = ('load__load_number', 'truck__unit_number', 'driver__employee_id')
    ordering      = ('-start_datetime',)
    readonly_fields = ('distance_miles',)
    inlines       = [TripEventInline]


@admin.register(TripEvent)
class TripEventAdmin(admin.ModelAdmin):
    list_display  = ('trip', 'event_type', 'description', 'recorded_at', 'recorded_by')
    list_filter   = ('event_type',)
    search_fields = ('trip__id', 'description')
    ordering      = ('-recorded_at',)


# ─────────────────────────────────────────
# Maintenance
# ─────────────────────────────────────────
@admin.register(MaintenanceHistory)
class MaintenanceHistoryAdmin(admin.ModelAdmin):
    list_display  = ('truck', 'maintenance_type', 'date_performed',
                     'mileage_at_service', 'total_cost', 'status', 'vendor')
    list_filter   = ('maintenance_type', 'status')
    search_fields = ('truck__unit_number', 'performed_by', 'description')
    ordering      = ('-date_performed',)
    date_hierarchy = 'date_performed'
    readonly_fields = ('created_at',)


@admin.register(PreventiveMaintenance)
class PreventiveMaintenanceAdmin(admin.ModelAdmin):
    list_display  = ('truck', 'pm_type', 'last_performed_date', 'next_due_date',
                     'next_due_mileage', 'status')
    list_filter   = ('status', 'pm_type')
    search_fields = ('truck__unit_number', 'pm_type')
    ordering      = ('next_due_date',)
    readonly_fields = ('next_due_date', 'next_due_mileage')


@admin.register(RepairOrder)
class RepairOrderAdmin(admin.ModelAdmin):
    list_display  = ('truck', 'priority', 'status', 'reported_by', 'reported_date',
                     'estimated_cost', 'actual_cost', 'vendor')
    list_filter   = ('status', 'priority', 'reported_by')
    search_fields = ('truck__unit_number', 'issue_description', 'root_cause')
    ordering      = ('-reported_date',)
    date_hierarchy = 'reported_date'
    readonly_fields = ('reported_date',)


@admin.register(Downtime)
class DowntimeAdmin(admin.ModelAdmin):
    list_display  = ('truck', 'reason', 'start_datetime', 'end_datetime',
                     'total_hours', 'revenue_lost_est')
    list_filter   = ('reason',)
    search_fields = ('truck__unit_number', 'notes')
    ordering      = ('-start_datetime',)
    readonly_fields = ('total_hours',)


# ─────────────────────────────────────────
# Inventory
# ─────────────────────────────────────────
class InventoryTransactionInline(admin.TabularInline):
    model  = InventoryTransaction
    extra  = 0
    fields = ('transaction_type', 'quantity', 'unit_cost', 'performed_by', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display  = ('part_name', 'part_number', 'category', 'quantity_on_hand',
                     'reorder_level', 'unit_cost', 'reorder_status', 'supplier')
    list_filter   = ('category',)
    search_fields = ('part_name', 'part_number', 'category')
    ordering      = ('part_name',)
    inlines       = [InventoryTransactionInline]

    def reorder_status(self, obj):
        if obj.needs_reorder:
            return format_html('<span style="color:red;font-weight:bold;">⚠ Reorder</span>')
        return format_html('<span style="color:green;">OK</span>')
    reorder_status.short_description = 'Stock Status'


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display  = ('part', 'transaction_type', 'quantity', 'unit_cost',
                     'performed_by', 'created_at')
    list_filter   = ('transaction_type',)
    search_fields = ('part__part_name', 'part__part_number')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at',)


# ─────────────────────────────────────────
# Alerts & Notifications
# ─────────────────────────────────────────
class NotificationInline(admin.TabularInline):
    model  = Notification
    extra  = 0
    fields = ('user', 'channel', 'is_read', 'sent_at')
    readonly_fields = ('sent_at',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ('alert_type', 'priority', 'truck', 'message_short',
                     'is_resolved', 'created_at')
    list_filter   = ('alert_type', 'priority', 'is_resolved')
    search_fields = ('message', 'truck__unit_number')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at',)
    inlines       = [NotificationInline]

    def message_short(self, obj):
        return obj.message[:80] + '…' if len(obj.message) > 80 else obj.message
    message_short.short_description = 'Message'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'alert', 'channel', 'is_read', 'sent_at')
    list_filter   = ('channel', 'is_read')
    search_fields = ('user__username', 'alert__alert_type')
    ordering      = ('-sent_at',)
    readonly_fields = ('sent_at',)


# ─────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('user', 'action', 'table_name', 'record_id', 'ip_address', 'created_at')
    list_filter   = ('action', 'table_name')
    search_fields = ('user__username', 'table_name', 'ip_address')
    ordering      = ('-created_at',)
    readonly_fields = ('user', 'action', 'table_name', 'record_id',
                       'old_data', 'new_data', 'ip_address', 'user_agent', 'created_at')

    def has_add_permission(self, request):
        return False  # Audit logs are system-generated only

    def has_delete_permission(self, request, obj=None):
        return False  # Immutable


# ─────────────────────────────────────────
# AI & ML
# ─────────────────────────────────────────
class AIMessageInline(admin.TabularInline):
    model  = AIMessage
    extra  = 0
    fields = ('role', 'content', 'created_at')
    readonly_fields = ('created_at',)


class AIActionInline(admin.TabularInline):
    model  = AIAction
    extra  = 0
    fields = ('action_type', 'status', 'approved_by', 'executed_at')
    readonly_fields = ('executed_at',)


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display  = ('session_id', 'user', 'title', 'started_at', 'ended_at')
    search_fields = ('session_id', 'user__username', 'title')
    ordering      = ('-started_at',)
    readonly_fields = ('session_id', 'started_at')
    inlines       = [AIMessageInline, AIActionInline]


@admin.register(AIAction)
class AIActionAdmin(admin.ModelAdmin):
    list_display  = ('action_type', 'status', 'approved_by', 'executed_at', 'created_at')
    list_filter   = ('status', 'action_type')
    search_fields = ('action_type',)
    ordering      = ('-created_at',)
    readonly_fields = ('created_at', 'executed_at')


@admin.register(MLPrediction)
class MLPredictionAdmin(admin.ModelAdmin):
    list_display  = ('prediction_type', 'truck', 'driver', 'confidence',
                     'model_version', 'is_actioned', 'generated_at')
    list_filter   = ('prediction_type', 'is_actioned')
    search_fields = ('truck__unit_number', 'driver__employee_id', 'model_version')
    ordering      = ('-generated_at',)
    readonly_fields = ('generated_at',)


