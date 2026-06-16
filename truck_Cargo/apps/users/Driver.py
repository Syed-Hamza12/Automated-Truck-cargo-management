import random

# from rest_framework.views import APIView
from django.http import JsonResponse
import json
from apps.models import User
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

        return JsonResponse({

            "username": request.user.username

        })

