from celery import shared_task
import time

@shared_task(queue='high')
def send_otp(phone, otp):

    print(
        f"Sending {otp} to {phone}"
    )