import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from google import genai
import asyncio

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# get email configuration from environment
def get_email_config():
    return {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'sender_email': os.getenv('SENDER_EMAIL'),
        'sender_password': os.getenv('SENDER_PASSWORD'),
        'sender_name': os.getenv('SENDER_NAME', 'HR Team')
    }

# use ai to personalize the interview confimation mail :D
async def generate_personalized_email(
    candidate_name: str,
    interview_datetime: str,
    job_description: str,
    calendar_link: str = ""
) -> str:
    try:
        api_key = os.getenv("AI_API_KEY")
        # if the api key just doesn't work then create a fallback email
        if not api_key:
            return create_fallback_email(candidate_name, interview_datetime, calendar_link) 
        
        client = genai.Client(api_key=api_key)
        
        # parse the datetime for better formatting
        dt = datetime.fromisoformat(interview_datetime)
        formatted_date = dt.strftime("%A, %B %d, %Y")
        formatted_time = dt.strftime("%I:%M %p UTC")
        
        prompt = f"""
Generate a professional, warm, and personalized interview confirmation email.

Candidate Name: {candidate_name}
Interview Date: {formatted_date}
Interview Time: {formatted_time}
Calendar Link: {calendar_link if calendar_link else "Will be sent separately"}

Job Description Summary:
{job_description[:500]}...

Requirements:
1. Professional and welcoming tone
2. Confirm interview details clearly
3. Provide preparation tips
4. Include what to expect during the interview
5. Contact information for questions
6. Format as HTML with proper styling

Generate ONLY the HTML email body (no subject line).
"""
        
        resp = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt
            )
        )
        
        email_content = resp.text
        
        # extract the AI html if the response is wrapped in code blocks
        import re
        match = re.search(r'```html\s*(.*?)\s*```', email_content, re.DOTALL)
        if match:
            email_content = match.group(1)
        
        return email_content
        
    except Exception as e:
        print(f"Error generating personalized email: {e}")
        return create_fallback_email(candidate_name, interview_datetime, calendar_link)

# create a standard email template as fallback
def create_fallback_email(candidate_name: str, interview_datetime: str, calendar_link: str = "") -> str:
    dt = datetime.fromisoformat(interview_datetime)
    formatted_date = dt.strftime("%A, %B %d, %Y")
    formatted_time = dt.strftime("%I:%M %p UTC")
    
    calendar_section = ""
    if calendar_link:
        calendar_section = f'<p><a href="{calendar_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Add to Calendar</a></p>'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #ffffff; }}
            .footer {{ background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; }}
            .highlight {{ background-color: #e8f5e9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Interview Confirmation</h1>
            </div>
            <div class="content">
                <p>Dear {candidate_name},</p>
                
                <p>We are pleased to invite you for an interview regarding the position you applied for.</p>
                
                <div class="highlight">
                    <h3>Interview Details</h3>
                    <p><strong>Date:</strong> {formatted_date}</p>
                    <p><strong>Time:</strong> {formatted_time}</p>
                    <p><strong>Duration:</strong> Approximately 60 minutes</p>
                </div>
                
                {calendar_section}
                
                <h3>What to Expect</h3>
                <ul>
                    <li>Technical discussion about your experience and skills</li>
                    <li>Questions about your approach to problem-solving</li>
                    <li>Overview of our team and company culture</li>
                    <li>Opportunity for you to ask questions</li>
                </ul>
                
                <h3>Preparation Tips</h3>
                <ul>
                    <li>Review the job description and your application</li>
                    <li>Prepare examples of your relevant work experience</li>
                    <li>Test your internet connection and video setup (if virtual)</li>
                    <li>Prepare questions about the role and company</li>
                </ul>
                
                <p>If you need to reschedule or have any questions, please don't hesitate to contact us.</p>
                
                <p>We look forward to speaking with you!</p>
                
                <p>Best regards,<br>
                <strong>HR Team</strong></p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply directly to this email.</p>
                <p>For questions, contact us at hr@company.com</p>
            </div>
        </div>
    </body>
    </html>
    """

# send email via smtp
async def send_email(to_email: str, subject: str, html_content: str) -> Dict:
    config = get_email_config()
    
    if not config['sender_email'] or not config['sender_password']:
        print(f"Email credentials not configured. Would send to: {to_email}")
        return {
            'email': to_email,
            'status': 'mock_sent',
            'message': 'Email credentials not configured (mock send)'
        }
    
    try:
        # create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{config['sender_name']} <{config['sender_email']}>"
        message['To'] = to_email
        
        # attach HTML content
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        # send email using smtp
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['sender_email'], config['sender_password'])
            server.send_message(message)
        
        print(f"✓ Email sent successfully to {to_email}")
        return {
            'email': to_email,
            'status': 'sent',
            'message': 'Email sent successfully'
        }
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return {
            'email': to_email,
            'status': 'failed',
            'message': str(e)
        }

    
# send personalized confirmation emails to all scheduled candidates
async def send_confirmation_emails(
    scheduled_interviews: List[Dict],
    job_description: str
) -> List[Dict]:
    email_tasks = []
    
    for interview in scheduled_interviews:
        if interview['status'] not in ['scheduled', 'scheduled_mock']:
            continue
        
        candidate_name = interview['candidate_name']
        candidate_email = interview['candidate_email']
        interview_datetime = interview['interview_start']
        calendar_link = interview.get('calendar_link', '')
        
        # generate personalized email
        email_content = await generate_personalized_email(
            candidate_name=candidate_name,
            interview_datetime=interview_datetime,
            job_description=job_description,
            calendar_link=calendar_link
        )
        
        subject = f"Interview Confirmation - {candidate_name}"
        
        # send email
        email_task = send_email(candidate_email, subject, email_content)
        email_tasks.append(email_task)
    
    # send all emails concurrently
    email_results = await asyncio.gather(*email_tasks)
    
    return email_results

if __name__ == "__main__":
    # test
    async def test():
        test_interviews = [
            {
                'candidate_name': 'Alice Johnson',
                'candidate_email': 'alice@example.com',
                'interview_start': '2025-10-05T10:00:00',
                'interview_end': '2025-10-05T11:00:00',
                'calendar_link': 'https://calendar.google.com/calendar/event123',
                'status': 'scheduled'
            }
        ]
        
        test_jd = "Senior Python Developer with FastAPI and ML experience"
        
        results = await send_confirmation_emails(test_interviews, test_jd)
        
        for result in results:
            print(f"{result['email']}: {result['status']}")
    
    asyncio.run(test())