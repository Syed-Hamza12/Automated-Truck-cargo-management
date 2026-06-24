from django.http import JsonResponse
import json
from apps.models import Package, Trip, Truck, Driver, Load , dispatch_department
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def is_trip_locked(trip):

    return trip.status in [Trip.Status.CANCELLED] or trip.complete_approve == True

def get_department(user):
    return dispatch_department.objects.get(
        user=user
    )

def send_notification(channel_group, message , id):
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                channel_group,
                {
                    "type": "send_notification",
                    "value": { "trip_id":id , "event":message }
                }
            )

class Dispatcher_unassigned_packages(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Logic to fetch unassigned packages
        department = get_department(request.user)
        unassigned_packages = Package.objects.filter(load__isnull=True , dispatcher_department = department).values()
        return JsonResponse({"unassigned_packages": unassigned_packages}, status=200)
    
class Dispatcher_dashboard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        department = get_department(request.user)
        active_trips = Trip.objects.filter(status='Active' , dispatcher_department = department ).count()
        available_trucks = Truck.objects.filter(status='Active' , dispatcher_department = department).count()
        available_drivers = Driver.objects.filter(status='Active' , dispatcher_department = department).count()
        active_load = Load.objects.filter(dispatcher_department = department).count()
        unassigned_packages = Package.objects.filter(load__isnull=True , dispatcher_department = department).count()


        dashboard_data = {
            "department" : department.first(),
            "active_trips": active_trips,
            "available_trucks": available_trucks,
            "available_drivers": available_drivers,
            "Active_load" : active_load,
            "Unassgined_packages" : unassigned_packages
        }
        return JsonResponse(dashboard_data, status=200)
    
class available_truck(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        department = get_department(request.user)
        available_truck = Truck.objects.filter(status='Active' , dispatcher_department = department).values()
        return JsonResponse(available_truck, status=200)
    
class available_driver(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        department = get_department(request.user)
        driver = Driver.objects.filter(status='Active' , dispatcher_department = department).values()
        return JsonResponse(driver , status =200)

class trips(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        department =get_department (request.user)
        trips = Trip.objects.select_related("load").filter(
            dispatcher_department = department
        ).values()
        
        data = {
            "id" : trips.id,
            "load__origin" : trips.load.origin,
            "load__destination":trips.load.destination,
            "status" : trips.status,
            "truck" : trips.truck,
        }

        return JsonResponse(data , status =200)
    
class TripDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):

        trip = Trip.objects.prefetch_related(
            "loads"
        ).select_related(
            "truck",
            "driver"
        ).get(id=trip_id)

        data = {
            "trip_id": trip.id,
            "status": trip.status,
            "editable": not is_trip_locked(trip),


            "truck": {
                "id": trip.truck.id,
                "plate": trip.truck.license_plate
            },

            "driver": {
                "id": trip.driver.id,
                "name": trip.driver.user.get_full_name()
            },

            "loads": [
                {
                    "id": load.id,
                    "load_number": load.load_number,
                    "origin": load.origin,
                    "destination": load.destination
                }
                for load in trip.loads.all()
            ]
        }

        return JsonResponse(data , status =200)
    
class LoadDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, load_id):

        load = Load.objects.prefetch_related(
            "packages"
        ).get(id=load_id)

        data = {
            "id": load.id,
            "load_number": load.load_number,
            "origin": load.origin,
            "destination": load.destination,
            "weight" : load.weight_lbs,
            "delivery_contact_phone" : load.delivery_contact_phone,
            "destination_longitude" : load.destination_longitude,
            "pickup_contact_phone" : load.pickup_contact_phone,
            
            "packages": [
                {
                    "id": package.id,
                    "tracking_number": package.tracking_number,
                    "origin": package.origin,
                    "destination": package.destination
                }
                for package in load.packages.all()
            ]
        }

        return JsonResponse(data , status =200)
    
class PackageDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, package_id):

        package = Package.objects.get(
            id=package_id
        )

        data = {
            "tracking_number": package.tracking_number,

            "sender": {
                "name": package.sender_name,
                "phone": package.sender_phone
            },

            "receiver": {
                "name": package.receiver_name,
                "phone": package.receiver_phone
            },

            "origin": package.origin,
            "destination": package.destination,
            "weight": package.weight_kg,
            "status": package.status
        }

        return JsonResponse(data , status=200)
    

class TripEditDataAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):

        department = get_department(user=request.user)

        trip = Trip.objects.get(
            id=trip_id
        )

        if is_trip_locked(trip):
            return JsonResponse(
                {
                    "error": "Trip is locked"
                },
                status=400
            )

        trucks = Truck.objects.filter(
            status="Active",
            dispatcher_department=department
        ).values(
            "id",
            "unit_number",
            "license_plate",
            "weight_carry"
            
        )

        drivers = Driver.objects.filter(
            status="Active"
        ).values(
            "id",
            "employee_id",
            "user__first_name",
            "user__last_name",
            "preferred_shift"
        )

        active_loads = Trip.objects.filter(
            status=Trip.Status.ACTIVE
        ).exclude(
            id=trip.id
        ).values_list(
            "loads__id",
            flat=True
        )

        loads = Load.objects.exclude(
            id__in=active_loads
        ).values(
            "id",
            "load_number",
            "origin",
            "destination"
        )

        

        return JsonResponse({
            "trip": {
                "id": trip.id,
                "driver_id": trip.driver.id,
                "truck_id": trip.truck.id,
                "complete_approve": trip.complete_approve,
                "status": trip.status
            },
            "available_trucks": list(trucks),
            "available_drivers": list(drivers),
            "available_loads": list(loads),
            
        })
    
class UpdateTripAPIView(APIView):

    permission_classes = [IsAuthenticated]
# {
#     "driver_id": 7,
#     "truck_id": 3,    body
#     "load_ids": [1,2,5]
# }
    def post(self, request, trip_id):

        trip = Trip.objects.get(id=trip_id)

        if is_trip_locked(trip):
            return JsonResponse(
                {
                    "error": "Trip is locked"
                },
                status=400
            )

        data = request.data
        driver = Driver.objects.filter(id=data["driver_id"])
        truck = Truck.objects.filter(id=data["truck_id"])

        if trip.driver != driver:
            driver_group = f"user_{trip.driver.user.id}"
            send_notification(driver_group, "Trip Assign to different Driver" , trip.id)
            driver_group = f"user_{driver.user.id}"
            send_notification(driver_group, "new Trip Added", trip.id)



        if "driver_id" in data:
            trip.driver =  driver      

        if "truck_id" in data:
            trip.truck = truck

        trip.complete_approve = data["complete_approve"]

        trip.save()

        if "load_ids" in data:
            trip.loads.set(data["load_ids"])

        return JsonResponse({
            "message": "Trip updated successfully"
        })
    
class NewLoadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        department = get_department (user=request.user)

        packages = Package.objects.filter(
            load__isnull=True,
            dispatcher_department=department
        ).values(
            "id",
            "tracking_number",
            "origin",
            "destination",
            "weight_kg",
            "status"
        )
        

        return JsonResponse({
            "available_packages": list(packages)
        })
    

class CreateLoadAPIView(APIView):

# {
#     "load_number":"LOAD-001",
#     "origin":"Karachi",
#     "destination":"Lahore",
#     "pickup_contact_phone":"12345",    body
#     "delivery_contact_phone":"67890",
#     "destination_latitude":31.5204,
#     "destination_longitude":74.3587,
#     "package_ids":[1,2,3]
# }
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        department = get_department(request.user)

        data = request.data

        package_ids = data.get(
            "package_ids",
            []
        )

        already_assigned = Package.objects.filter(
            id__in=package_ids
        ).exclude(
            load__isnull=True
        )

        if already_assigned.exists():

            return JsonResponse({
                "error":
                "Some packages already assigned to another load",

                "package_ids":
                list(
                    already_assigned.values_list(
                        "id",
                        flat=True
                    )
                )
            }, status=400)

        load = Load.objects.create(
            load_number=data["load_number"],
            origin=data["origin"],
            destination=data["destination"],
            pickup_contact_phone=data.get(
                "pickup_contact_phone"
            ),
            delivery_contact_phone=data.get(
                "delivery_contact_phone"
            ),
            destination_latitude=data.get(
                "destination_latitude"
            ),
            destination_longitude=data.get(
                "destination_longitude"
            ),
            created_by=request.user,
            dispatcher_department=department
        )

        Package.objects.filter(
            id__in=package_ids
        ).update(
            load=load
        )

        return JsonResponse({
            "message":
            "Load created successfully",

            "load_id":
            load.id
        })
    
class LoadEditAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, load_id):

        load = Load.objects.prefetch_related(
            "packages"
        ).get(
            id=load_id
        )

        available_packages = Package.objects.filter(
            load__isnull=True
        ).values(
            "id",
            "tracking_number",
            "origin",
            "destination"
        )

        data = {

            "load": {
                "id": load.id,
                "load_number": load.load_number,
                "origin": load.origin,
                "destination": load.destination,
                "pickup_contact_phone":
                load.pickup_contact_phone,
                "delivery_contact_phone":
                load.delivery_contact_phone,
                "destination_latitude":
                load.destination_latitude,
                "destination_longitude":
                load.destination_longitude
            },

            "available_packages":
            list(available_packages),

            "assigned_packages": [
                {
                    "id": p.id,
                    "tracking_number": p.tracking_number
                }
                for p in load.packages.all()
            ]
        }

        return JsonResponse(data , status = 200)
    

class SaveLoadAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, load_id):

        load = Load.objects.get(
            id=load_id
        )

        data = request.data

        package_ids = data.get(
            "package_ids",
            []
        )

        conflict_packages = Package.objects.filter(
            id__in=package_ids
        ).exclude(
            Q(load__isnull=True)
            |
            Q(load=load)
        )

        if conflict_packages.exists():

            return JsonResponse({
                "error":
                "Some packages are already assigned",
                "assigned pakages": list(conflict_packages.value("id","tracking_number","origin","destination"))
            }, status=400)

        load.origin = data["origin"]
        load.destination = data["destination"]

        load.pickup_contact_phone = data.get(
            "pickup_contact_phone"
        )

        load.delivery_contact_phone = data.get(
            "delivery_contact_phone"
        )

        load.destination_latitude = data.get(
            "destination_latitude"
        )

        load.destination_longitude = data.get(
            "destination_longitude"
        )

        load.save()

        Package.objects.filter(
            load=load
        ).update(
            load=None
        )

        Package.objects.filter(
            id__in=package_ids
        ).update(
            load=load
        )

        return JsonResponse({
            "message":
            "Load updated successfully"
        })
    

class AddTripAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        department = get_department(
            request.user
        )

        drivers = Driver.objects.filter(
            status="Active",
            dispatcher_department=department
        ).values(
            "id",
            "employee_id",
            "user__first_name",
            "user__last_name"
        )

        trucks = Truck.objects.filter(
            status="Active",
            dispatcher_department=department
        ).values(
            "id",
            "unit_number",
            "license_plate"
        )

        active_loads = Trip.objects.filter(
            status=Trip.Status.ACTIVE
        ).values_list(
            "loads__id",
            flat=True
        )

        loads = Load.objects.filter(
            dispatcher_department=department
        ).exclude(
            id__in=active_loads
        ).values(
            "id",
            "load_number",
            "origin",
            "destination"
        )

        return JsonResponse({
            "drivers": list(drivers),
            "trucks": list(trucks),
            "loads": list(loads)
        })
    
class CreateTripAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        department = get_department(
            request.user
        )

        data = request.data

        load_ids = data["load_ids"]
        driver = Driver.objects.filter(id=data["driver_id"])
        truck = Truck.objects.filter(id=data["truck_id"])


        if Trip.objects.filter(
            status=Trip.Status.ACTIVE,
            loads__in=load_ids
        ).exists():

            return JsonResponse({
                "error":
                "One or more loads already assigned"
            }, status=400)

        trip = Trip.objects.create(
            driver=driver,
            truck=truck,
            assigned_by=request.user,
            dispatcher_department=department,
            status=Trip.Status.ACTIVE
        )

        trip.loads.set(load_ids)

        driver_group = f"user_{driver.user.id}"
        send_notification(driver_group, "trip Added" , trip.id)

        return JsonResponse({
            "message":
            "Trip created successfully",

            "trip_id":
            trip.id
        })