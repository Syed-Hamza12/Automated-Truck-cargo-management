import os
import groq
from AI.prompts.prompt import truck_issue_reported_Prompt
import json
import re
from dotenv import load_dotenv
load_dotenv()

client_groq = groq.Groq(
    api_key=os.environ.get("groq")
)

def llm_analyze_issue(issue):
    prompt = truck_issue_reported_Prompt(issue)

    try:
        response = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        content = response.choices[0].message.content.strip()

        print("RAW:", content)

        content = re.sub(r"^```json", "", content)
        content = re.sub(r"```$", "", content)
        content = content.strip()

        return json.loads(content)

    except Exception as e:
        print("error:", e)

        return {
            "severity": "Unknown",
            "reason": issue.description
        }