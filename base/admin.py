from django.contrib import admin

from base.models import Appointment, Doctor, Patient, Slot, State


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'date_modified', 'date_created')
    search_fields = ('name',)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'date_created')
    search_fields = ('name',)
    exclude = ('password',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'date_created')
    search_fields = ('name', 'phone_number')
    exclude = ('password',)


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_time', 'status', 'date_created')
    list_filter = ('status',)
    search_fields = ('doctor__name',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'slot', 'date', 'state', 'cancellation_reason', 'date_created')
    list_filter = ('state', 'date')
    search_fields = ('patient__name', 'slot__doctor__name')
