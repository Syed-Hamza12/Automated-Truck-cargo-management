from django.http import JsonResponse
import json
from apps.models import Driver, IssueReport, Trip, Truck
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from celery_tasks.notification_worker import process_issue_report


class DriverProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        Driver_object = Driver.objects.filter(user_id=user_id).first()
        return JsonResponse({
            "User_Role" : "Driver",
            "username":request.user.username,
            "phone":request.user.phone,
            "license_number":Driver_object.license_number,
            "employee_id":Driver_object.employee_id,
        })
    

class Driver_trip_history(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        Trip_object = Trip.objects.filter(driver__user_id=request.user.id)
        print(Trip_object.first())
        
        trip = Trip_object.values(
            "id",
            "load__origin",
            "load__destination",
            "status",
            "start_datetime"
        )
        
        return JsonResponse({
            "trip_history": list(trip)
        })


class Driver_actve_trip(APIView):
   
    permission_classes = [IsAuthenticated]
    def get(self, request):
        Trip_object = Trip.objects.filter(driver__user_id=request.user.id, status="Planned")
        trip = Trip_object.values(
            "id",
            "load__origin",
            "load__destination",
            "status",
            "start_datetime"
        )
        return JsonResponse({
            "trip_history": list(trip)
        })

class TripInfo(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        trip = Trip.objects.select_related("load", "truck").filter(
            driver__user_id=request.user.id,
            id=trip_id
        ).first()

        if not trip:
            return JsonResponse({"error": "Trip not found"}, status=404)

        # latest truck location
        truck_location = trip.truck.locations.order_by("-recorded_at").first()

        trip_data = {
            "load_number": trip.load.load_number,
            "load_origin": trip.load.origin,
            "load_destination": trip.load.destination,
            "load_weight": trip.load.weight_lbs,
            "load_pickup_contact_phone": trip.load.pickup_contact_phone,
            "load_delivery_contact_phone": trip.load.delivery_contact_phone,
            "truck_latitude": truck_location.latitude if truck_location else None,
            "truck_longitude": truck_location.longitude if truck_location else None,
            "truck_number_plate": trip.truck.license_plate,
            "status": trip.status,
            "start_datetime": trip.start_datetime,
            "end_datetime": trip.end_datetime,
            "trip_assigned_by": trip.assigned_by.username if trip.assigned_by else None
        }

        return JsonResponse({"trip_info": trip_data})


class Driver_issue_report(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)
        license_plate = data.get("license_plate")
        description = data.get("description")

        truck = Truck.objects.filter(
            license_plate=license_plate,
        ).first()

        if not truck:
            return JsonResponse({"error": "Truck not found"}, status=404)

        issue_report = IssueReport.objects.create(
            truck=truck,
            reported_by =request.user,
            description=description
        )

        # Trigger the Celery task to process the issue report
        process_issue_report.delay(
            issue_report.id,
            truck.dispatcher_department.user.id if truck.dispatcher_department else None,
            truck.fleet_department.user.id if truck.fleet_department else None
        )

        return JsonResponse({"message": "Issue reported successfully."})