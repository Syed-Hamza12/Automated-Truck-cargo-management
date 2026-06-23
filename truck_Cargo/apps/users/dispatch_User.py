from django.http import JsonResponse
import json
from apps.models import Package, Trip, Truck, Driver, Load , dispatch_department
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class Dispatcher_unassigned_packages(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Logic to fetch unassigned packages
        department = dispatch_department.objects.filter(user = request.user)
        unassigned_packages = Package.objects.filter(load__isnull=True , dispatcher_department = department).values()
        return JsonResponse({"unassigned_packages": unassigned_packages}, status=200)
    
class Dispatcher_dashboard(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        department = dispatch_department.objects.filter(user = request.user)
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
        department = dispatch_department.objects.filter(user = request.user)
        available_truck = Truck.objects.filter(status='Active' , dispatcher_department = department).values()
        return JsonResponse(available_truck, status=200)
    
class available_driver(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        department = dispatch_department.objects.filter(user = request.user)
        driver = Driver.objects.filter(status='Active' , dispatcher_department = department).values()
        return JsonResponse(driver , status =200)

class trips(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        department = dispatch_department.objects.filter(user = request.user)
        trips = Trip.objects.filter(dispatcher_department = department  ).values(
            "id",
            "load__origin",
            "load__destination",
            "status",
            "truck"
        )

        return JsonResponse(trips , status =200)
    
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