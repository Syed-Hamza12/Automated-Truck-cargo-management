from celery import shared_task
import time
from apps.models import IssueReport , Alert , Notification ,User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from AI.LLM.llm import llm_analyze_issue

def send_notification(channel_group, event_type):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            channel_group,
            {
                "type": "send_notification",
                "value": {
                    "event": event_type,  
                    
                }
            }
        )


@shared_task(queue='high')
def process_issue_report(issue_id , dispatcher_user_id , fleet_manager_user_id):

    dispatcher_user = User.objects.filter(id=dispatcher_user_id).first()
    fleet_manager_user = User.objects.filter(id=fleet_manager_user_id).first()

    issue = IssueReport.objects.filter(id=issue_id).first()

    analysis = llm_analyze_issue(issue)

    if not isinstance(analysis, dict):
        analysis = {
            "severity": "Unknown",
            "reason": issue.description
        }

    if analysis["severity"] == "Unknown":
         alert_type = 'Truck Issue Reported'

    severity = analysis["severity"] 
    if severity == 'High' or severity == 'Critical':
        alert_type = 'Truck Out of Service'
    else:
        alert_type = 'Truck Inspection Required'
    
    alert = Alert.objects.create(
    alert_type=alert_type,
    priority=analysis["severity"],
    truck=issue.truck,
    message=analysis["reason"]
    )
   
    Notification.objects.create(
    alert=alert,
    user=fleet_manager_user,
    channel="In-App"
    )
    if alert_type == 'Truck Out of Service':
        Notification.objects.create(
        alert=alert,
        user=dispatcher_user,
        channel="In-App"
        )
        truck_id = issue.truck.id
        dispatcher = f"user_{dispatcher_user.id}"
        send_notification(dispatcher, f"Truck {truck_id} and License Plate {issue.truck.license_plate} has Issue. Please reassign the trip.")

    fleet = f"user_{fleet_manager_user.id}"
    send_notification(fleet, analysis["reason"])
    
   
    

