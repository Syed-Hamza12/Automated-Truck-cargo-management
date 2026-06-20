from django.contrib import admin
from django.urls import path , include  
from apps.users.Driver import Driver_issue_report, Driver_trip_history, RequestOTPView , VerifyOTPView , DriverProfileView , Driver_actve_trip, TripInfo
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
path('Driver-request-otp/',RequestOTPView,name="request_otp"),
path(    "verify-otp/",    VerifyOTPView , name="verify_otp"),
path('Driver-profile/', DriverProfileView.as_view(), name="driver_profile"),
path('driver-trip-history/', Driver_trip_history.as_view(), name="driver_trip_history"),
path('driver-active-trip/', Driver_actve_trip.as_view(), name="driver_active_trip"),
path('trip-info/<int:trip_id>/', TripInfo.as_view(), name="trip_info"),
path('Driver-report-issue/', Driver_issue_report.as_view(), name="driver_report_issue"),
# Endpoint to login and get tokens
path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Endpoint to get a new access token using a refresh token
path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
