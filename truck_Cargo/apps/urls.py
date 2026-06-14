from django.contrib import admin
from django.urls import path , include  
from apps.users.Driver import RequestOTPView , VerifyOTPView , DriverProfileView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
path('Driver-request-otp/',RequestOTPView,name="request_otp"),
path(    "verify-otp/",    VerifyOTPView , name="verify_otp"),
path('Driver-profile/', DriverProfileView.as_view(), name="driver_profile"),

# Endpoint to login and get tokens
path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # Endpoint to get a new access token using a refresh token
path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
