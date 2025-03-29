from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import time
from io import StringIO
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/send-emails": {"origins": "http://localhost:3000"}})  # Update later for Vercel

# Set up a log file
logging.basicConfig(filename='email_sender.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s: %(message)s')

# Email configuration from environment variables
sender_email = os.environ.get("EMAIL_USER")
password = os.environ.get("EMAIL_PASSWORD")
default_subject = os.environ.get("EMAIL_SUBJECT", "Greetings with Attachment")

@app.route('/send-emails', methods=['POST'])
def send_emails():
    if 'csv_file' not in request.files or 'attachment' not in request.files:
        return jsonify({"error": "CSV file and attachment are required"}), 400
    
    csv_file = request.files['csv_file']
    attachment_file = request.files['attachment']
    
    # Get custom email content or use default
    email_subject = request.form.get('subject', default_subject)
    email_body = request.form.get('email_body', "Dear {name},\n\nThis is an automated message.\n\nBest regards,\nAutomated System")
    
    # Validate credentials are set
    if not sender_email or not password:
        logging.error("Email credentials not set in environment variables")
        return jsonify({
            "error": "Server configuration error. Email credentials not set in .env file. Please add EMAIL_USER and EMAIL_PASSWORD."
        }), 500
    
    # Save attachment temporarily
    attachment_path = f"temp_{attachment_file.filename}"
    attachment_file.save(attachment_path)
    
    # Read CSV
    try:
        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_content))
        
        # Check for required columns
        required_columns = ['Email', 'Name']
        first_row = next(csv_reader, None)
        if not first_row or not all(col in first_row for col in required_columns):
            os.remove(attachment_path)
            return jsonify({"error": "CSV must contain 'Email' and 'Name' columns"}), 400
        
        # Reset CSV reader
        csv_file.seek(0)
        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_content))
        
        # Connect to Gmail
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                try:
                    server.login(sender_email, password)
                except smtplib.SMTPAuthenticationError as auth_error:
                    logging.error(f"Gmail authentication failed: {str(auth_error)}")
                    return jsonify({
                        "error": "Gmail authentication failed. Please ensure you're using an App Password and not your regular password. "
                                "Go to https://myaccount.google.com/ > Security > 2-Step Verification > App passwords to generate one."
                    }), 401
                
                success_count = 0
                error_count = 0
                
                for row in csv_reader:
                    recipient_email = row.get('Email', '').strip()
                    recipient_name = row.get('Name', '').strip()
                    
                    if not recipient_email:
                        logging.warning(f"Skipping row with empty email: {row}")
                        error_count += 1
                        continue
                    
                    try:
                        # Make the email
                        msg = MIMEMultipart()
                        msg['Subject'] = email_subject
                        msg['From'] = sender_email
                        msg['To'] = recipient_email
                        
                        # Personalize the email body with recipient's name
                        personalized_body = email_body.format(name=recipient_name or 'Recipient')
                        msg.attach(MIMEText(personalized_body, 'plain'))
                        
                        # Add attachment
                        with open(attachment_path, 'rb') as f:
                            filename = os.path.basename(attachment_file.filename)
                            # Determine subtype based on file extension
                            file_ext = os.path.splitext(filename)[1].lower()
                            if file_ext == '.pdf':
                                subtype = 'pdf'
                            elif file_ext in ['.jpg', '.jpeg']:
                                subtype = 'jpeg'
                            elif file_ext == '.png':
                                subtype = 'png'
                            else:
                                subtype = 'octet-stream'
                            
                            attachment = MIMEApplication(f.read(), _subtype=subtype)
                            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                            msg.attach(attachment)
                        
                        # Send email
                        server.send_message(msg)
                        logging.info(f"Sent to {recipient_name} ({recipient_email})")
                        success_count += 1
                        time.sleep(1)  # Delay to avoid Gmail limits
                    
                    except Exception as e:
                        logging.error(f"Failed to send to {recipient_email}: {str(e)}")
                        error_count += 1
                
                return jsonify({
                    "message": f"Process completed. {success_count} emails sent successfully, {error_count} failed.",
                    "success": success_count,
                    "errors": error_count
                }), 200
                
        except Exception as e:
            logging.error(f"SMTP Connection error: {str(e)}")
            return jsonify({"error": f"Failed to connect to email server: {str(e)}"}), 500
            
    except Exception as e:
        logging.error(f"General error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        # Clean up temporary file
        if os.path.exists(attachment_path):
            os.remove(attachment_path)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)