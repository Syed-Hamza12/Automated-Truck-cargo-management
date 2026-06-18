from pyclbr import Class
import random

# from rest_framework.views import APIView
from django.http import JsonResponse
import json
from apps.models import Driver, Trip, User
from apps.utils.redis import redis_client
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from celery_tasks.whatsapp_worker import send_otp




@csrf_exempt
def RequestOTPView(request):
    if request.method == "POST":
        try:
            # Parse the raw bytes body into a dictionary
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        username = data.get("username")
        phone = data.get("phone")

        user = User.objects.filter(
            username=username,
            phone=phone,
            role=User.Role.DRIVER
        ).first()

        if not user:
            return JsonResponse(
                {"error":"Driver not found"},
                status=400
            )

        otp = str(random.randint(1000,9999))
        
        send_otp.delay(
            user.phone,
            otp
        )

        redis_client.set(
            f"otp:{user.id}",
            otp,
            ex=300
        )

        return JsonResponse(
            {"message":"OTP Sent"}
        )

@csrf_exempt
def VerifyOTPView(request):
    if request.method == "POST":
        try:
            # Parse the raw bytes body into a dictionary
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        username = data.get("username")
        otp = data.get("otp")

        user = User.objects.filter(
            username=username
        ).first()

        if not user:
            return JsonResponse(
                {"error":"User not found"},
                status=400
            )

        stored_otp = redis_client.get(
            f"otp:{user.id}"
        )

        if stored_otp != otp:
            print(f"Stored OTP: {stored_otp}, Provided OTP: {otp}")
            return JsonResponse(
                {"error":"Invalid OTP"},
                status=400
            )

        redis_client.delete(
            f"otp:{user.id}"
        )

        refresh = RefreshToken.for_user(user)

        return JsonResponse({

            "access": str(
                refresh.access_token
            ),

            "refresh": str(
                refresh
            )

        })
    

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
