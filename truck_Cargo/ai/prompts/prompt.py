def truck_issue_reported_Prompt(issue):
    return f"""
    You are an expert fleet maintenance AI assistant. Analyze the truck issue report and determine its severity and the core reasoning.

    [TRAINING EXAMPLES]

    Example 1 (Low Severity):
    Input:
    - Truck ID: TRK-102
    - License Plate: 3ABC12
    - Issue Description: The driver side windshield wiper is leaving streaks during heavy rain. Needs replacement.
    - Reported At: 2026-06-19 08:15:00
    Output:
    {{
        "severity": "Low",
        "reason": "Truck TRK-102 (License Plate: 3ABC12) needs a replacement driver-side windshield wiper due to streaking. It is safe to drive but should be scheduled for routine maintenance."
    }}

    Example 2 (High Severity):
    Input:
    - Truck ID: TX-4092
    - License Plate: 7XYZ89
    - Issue Description: Driver reports air pressure warning light is flashing and brakes are feeling extremely spongy. Truck is currently pulled over on the highway shoulder.
    - Reported At: 2026-06-20 11:30:00
    Output:
    {{
        "severity": "Critical",
        "reason": "Truck TX-4092 (License Plate: 7XYZ89) has an active brake air pressure failure, posing an immediate safety hazard. The vehicle must be taken out of service immediately."
    }}

    [ACTUAL TASK TO EVALUATE]
    Analyze the following report and output the result using the exact same JSON format shown in the training examples. Do not include markdown blocks like ```json or any extra text.

    Input:
    - Truck ID: {issue.truck.id}
    - License Plate: {issue.truck.license_plate}
    - Issue Description: {issue.description}
    - Reported At: {issue.reported_at}
    Output:
    """