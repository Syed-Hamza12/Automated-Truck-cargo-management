from celery import shared_task
import time
from apps.models import IssueReport , Alert , Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from AI.LLM.llm import llm_analyze_issue



@shared_task(queue='medium')
def process_issue_report(issue_id , dispatcher_id , fleet_manager_id):

    issue = IssueReport.objects.filter(id=issue_id).first()

    analysis = llm_analyze_issue(issue)

    if analysis == "Something went wrong.":
         analysis["severity"] = "Unknown"
         analysis["reason"] = issue.description
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
    user=fleet_manager_id,
    channel="In-App"
    )
    if alert_type == 'Truck Out of Service':
        Notification.objects.create(
        alert=alert,
        user=dispatcher_id,
        channel="In-App"
        )
        truck_id = issue.truck.id
        dispatcher = f"user_{dispatcher_id}"
        send_notification(dispatcher, f"Truck {truck_id} and License Plate {issue.truck.license_plate} has Issue. Please reassign the trip.")

    fleet = f"user_{fleet_manager_id}"
    send_notification(fleet, alert_type)
    
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
    
    

