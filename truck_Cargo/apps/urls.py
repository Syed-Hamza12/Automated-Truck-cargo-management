from django.contrib import admin
from django.urls import path , include  
from apps.users.Driver import Driver_issue_report, Driver_trip_history,DriverProfileView , Driver_actve_trip, TripInfo
from apps.users.User import RequestOTPView, VerifyOTPView
from apps.users.dispatch_User import (AddTripAPIView, CreateLoadAPIView, CreateTripAPIView, LoadEditAPIView, SaveLoadAPIView, available_driver , available_truck , Dispatcher_dashboard  , Dispatcher_unassigned_packages , trips ,TripDetailAPIView ,
 LoadDetailAPIView , PackageDetailAPIView , TripEditDataAPIView , UpdateTripAPIView , NewLoadAPIView)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from apps.dispatch.AI_suggestion_engine import SuggestLoadsAPIView, SuggestTripsAPIView

urlpatterns = [
path('login-request-otp/',RequestOTPView,name="request_otp"),
path(    "verify-otp/",    VerifyOTPView , name="verify_otp"),
path('Driver-profile/', DriverProfileView.as_view(), name="driver_profile"),
path('driver-trip-history/', Driver_trip_history.as_view(), name="driver_trip_history"),
path('driver-active-trip/', Driver_actve_trip.as_view(), name="driver_active_trip"),
path('trip-info/<int:trip_id>/', TripInfo.as_view(), name="trip_info"),
path('Driver-report-issue/', Driver_issue_report.as_view(), name="driver_report_issue"),
path('packages/unassigned/',Dispatcher_unassigned_packages.as_views() , name=""),
path('dispatcher/dashboard/', Dispatcher_dashboard.as_views() , name=""),
# path('dispatcher/load-suggestions/', .as_view(), name=""),
path('dispatcher/available-trucks/', available_truck.as_view(), name=""),
path('dispatcher/available-drivers/', available_driver.as_view(), name=""),
path('dispatcher/trip/', trips.as_view(), name=""),
path('dispatcher/trip/<int:trip_id>/', TripDetailAPIView.as_view(), name=""),
path('dispatcher/load/<int:load_id>/', LoadDetailAPIView.as_view(), name=""),
path('dispatcher/package/<int:package_id>/', PackageDetailAPIView.as_view(), name=""),
path('dispatcher/trips/<int:trip_id>/edit-data/', TripEditDataAPIView.as_view(), name=""),
path('dispatcher/trips/<int:trip_id>/update/', UpdateTripAPIView.as_view(), name=""),
path('/dispatcher/newload/', NewLoadAPIView.as_view(), name=""),
path('/dispatcher/loadcreate/', CreateLoadAPIView.as_view(), name=""),
path('/dispatcher/load/<int:id>/edit/', LoadEditAPIView.as_view(), name=""),
path('/dispatcher/load/<int:id>/save/', SaveLoadAPIView.as_view(), name=""),
path('/dispatcher/addtrip/', AddTripAPIView.as_view(), name=""),
path('/dispatcher/createtrip/', CreateTripAPIView.as_view(), name=""),
path('/dispatcher/SuggestLoadsAPIView', SuggestLoadsAPIView.as_view(), name=""),
path('/dispatcher/SuggestTripsAPIView', SuggestTripsAPIView.as_view(), name=""),


# Endpoint to login and get tokens
path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Endpoint to get a new access token using a refresh token
path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
