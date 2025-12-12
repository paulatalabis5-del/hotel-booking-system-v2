from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import jwt
from datetime import datetime, timedelta
from models import (User, Room, Booking, Amenity, BookingAmenity, Rating, Notification, Payment,
                   CheckInOut, RoomStatus, CleaningTask, SecurityPatrol, SecurityIncident, 
                   WorkOrder, Equipment, EquipmentMaintenance, DailyReport, StaffPerformance, Attendance,
                   Payroll, PayrollBonus, PayrollDeduction, Schedule, ServiceRequest, InventoryItem, InventoryTransaction)
from extensions import db
import smtplib
import socket
from email.mime.text import MIMEText
import random
import os
from payment_service import gcash_service
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Create API blueprint
api_bp = Blueprint('unique_api_blueprint_xyz789', __name__, url_prefix='/api')

# JWT Secret Key (should be in environment variables in production)
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# SendGrid Email configuration
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@easyhotel.com')

# Legacy Gmail configuration (fallback)
EMAIL_SERVER = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USERNAME = 'hotelmanagementsystem48@gmail.com'
EMAIL_PASSWORD = 'gtyxoxlvpftyoziv'  # App Password without spaces

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def send_verification_email(email, verification_code):
    """Send verification email to user using SendGrid"""
    print("\n" + "-"*60)
    print("📧 [SENDGRID] Starting email send process")
    print("-"*60)
    try:
        print(f"📧 [SENDGRID] Recipient: {email}")
        print(f"📧 [SENDGRID] From: {EMAIL_FROM}")
        print(f"📧 [SENDGRID] API Key configured: {'Yes' if SENDGRID_API_KEY else 'No'}")
        print(f"📧 [SENDGRID] Verification code: {verification_code}")
        
        if not SENDGRID_API_KEY:
            print("❌ [SENDGRID] No API key configured, falling back to SMTP")
            return send_verification_email_smtp(email, verification_code)
        
        # Create the email content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🏨 Easy Hotel</h1>
                <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Welcome to our hotel booking platform!</p>
            </div>
            
            <div style="background: white; padding: 40px; border: 1px solid #e0e0e0; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Email Verification Required</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Thank you for registering with Easy Hotel! To complete your account setup, please verify your email address.
                </p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                    <p style="color: #333; margin: 0 0 10px 0; font-size: 14px;">Your verification code is:</p>
                    <div style="font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 3px; font-family: monospace;">
                        {verification_code}
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px; line-height: 1.6;">
                    Please enter this code in the app to verify your email address. This code will expire in 15 minutes.
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    If you didn't create an account with Easy Hotel, please ignore this email.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>© 2024 Easy Hotel. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Welcome to Easy Hotel!
        
        Your verification code is: {verification_code}
        
        Please enter this code in the app to complete your registration.
        This code will expire in 15 minutes.
        
        If you did not request this registration, please ignore this email.
        
        Best regards,
        Easy Hotel Team
        """
        
        # Create the email message
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=email,
            subject='Easy Hotel - Email Verification Code',
            html_content=html_content,
            plain_text_content=plain_content
        )
        
        print(f"📧 [SENDGRID] Sending email via SendGrid API...")
        
        # Send the email
        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ [SENDGRID] Email sent successfully!")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.body}")
        print(f"   Response Headers: {response.headers}")
        print("-"*60 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ [SENDGRID] Error sending email: {str(e)}")
        print(f"❌ [SENDGRID] Error type: {type(e).__name__}")
        import traceback
        print(f"❌ [SENDGRID] Traceback:")
        traceback.print_exc()
        print("-"*60 + "\n")
        
        # Fallback to SMTP if SendGrid fails
        print("🔄 [SENDGRID] Falling back to SMTP...")
        return send_verification_email_smtp(email, verification_code)

def send_verification_email_smtp(email, verification_code):
    """Fallback SMTP email sending function"""
    print("\n" + "-"*60)
    print("📧 [SMTP] Starting SMTP email send process")
    print("-"*60)
    try:
        print(f"📧 [SMTP] Recipient: {email}")
        print(f"📧 [SMTP] SMTP Server: {EMAIL_SERVER}:{EMAIL_PORT}")
        print(f"📧 [SMTP] Username: {EMAIL_USERNAME}")
        print(f"📧 [SMTP] Verification code: {verification_code}")
        
        msg = MIMEText(f'''
        Welcome to Easy Hotel!
        
        Your verification code is: {verification_code}
        
        Please enter this code to complete your registration.
        
        If you did not request this registration, please ignore this email.
        
        Best regards,
        Easy Hotel Team
        ''')
        msg['Subject'] = 'Easy Hotel - Email Verification'
        msg['From'] = EMAIL_USERNAME
        msg['To'] = email
        
        print(f"📧 [SMTP] Connecting to SMTP server...")
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT, timeout=30) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USERNAME, [email], msg.as_string())
            print(f"✅ [SMTP] Email sent successfully to {email}")
        
        print("-"*60 + "\n")
        return True
    except Exception as e:
        print(f"❌ [SMTP] Error: {str(e)}")
        print("-"*60 + "\n")
        return False

# Authentication Routes
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        token = generate_token(user.id)
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_staff': user.is_staff,
                'staff_role': user.staff_role
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    print("\n" + "="*80)
    print("🔵 [REGISTER] Starting registration process")
    print("="*80)
    
    data = request.get_json()
    print(f"📦 [REGISTER] Received data: {data}")
    
    # Validation
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    phone_number = data.get('phone_number')
    verification_code = data.get('verification_code')
    
    print(f"👤 [REGISTER] Username: {username}")
    print(f"📧 [REGISTER] Email: {email}")
    print(f"📱 [REGISTER] Phone: {phone_number}")
    print(f"🔑 [REGISTER] Verification code provided: {verification_code is not None}")
    
    if not all([username, email, password, confirm_password, phone_number]):
        print("❌ [REGISTER] Missing required fields")
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    if password != confirm_password:
        print("❌ [REGISTER] Passwords do not match")
        return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
    
    # If verification code is provided, verify it
    if verification_code:
        print(f"🔍 [REGISTER] Verifying code: {verification_code}")
        # Check if verification code is valid
        pending_user = User.query.filter_by(email=email, is_verified=False).first()
        
        if not pending_user:
            print(f"❌ [REGISTER] No pending user found for email: {email}")
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400
        
        print(f"✅ [REGISTER] Found pending user: {pending_user.username}")
        print(f"🔑 [REGISTER] Expected code: {pending_user.verification_code}")
        print(f"🔑 [REGISTER] Provided code: {verification_code}")
        
        if pending_user.verification_code != verification_code:
            print("❌ [REGISTER] Verification code mismatch")
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400
        
        # Verify the user
        print("✅ [REGISTER] Verification code matched! Activating user...")
        pending_user.is_verified = True
        pending_user.verification_code = None
        db.session.commit()
        
        # Generate token and return success
        token = generate_token(pending_user.id)
        print(f"🎉 [REGISTER] User verified successfully! Token generated.")
        print("="*80 + "\n")
        return jsonify({
            'success': True, 
            'message': 'Registration successful',
            'token': token,
            'user': {
                'id': pending_user.id,
                'username': pending_user.username,
                'email': pending_user.email,
                'is_admin': pending_user.is_admin,
                'is_staff': pending_user.is_staff,
                'staff_role': pending_user.staff_role
            }
        })
    
    # Check if user already exists (only for new registrations)
    print("🔍 [REGISTER] Checking if user already exists...")
    existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        print(f"❌ [REGISTER] User already exists: {existing_user.email}")
        return jsonify({'success': False, 'message': 'User already exists'}), 400
    
    # Generate verification code
    verification_code = str(random.randint(100000, 999999))
    print(f"🔑 [REGISTER] Generated verification code: {verification_code}")
    
    # Create user with verification pending
    print("👤 [REGISTER] Creating new user in database...")
    new_user = User(
        username=username,
        email=email,
        phone_number=phone_number,
        is_verified=False,
        verification_code=verification_code
    )
    new_user.set_password(password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        print(f"✅ [REGISTER] User created successfully with ID: {new_user.id}")
    except Exception as e:
        print(f"❌ [REGISTER] Database error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    
    # Send verification email
    print(f"📧 [REGISTER] Attempting to send verification email to: {email}")
    email_sent = send_verification_email(email, verification_code)
    print(f"📧 [REGISTER] Email send result: {email_sent}")
    
    if email_sent:
        print(f"✅ [REGISTER] Registration successful! Verification email sent.")
        print(f"🔑 [REGISTER] User should check email for code: {verification_code}")
        print("="*80 + "\n")
        return jsonify({
            'success': True, 
            'message': 'Verification code sent to your email. Please check your inbox.',
            'requires_verification': True
        })
    else:
        # If email fails, delete the user and return error
        # This ensures proper verification is enforced
        print(f"❌ [REGISTER] Email send failed! Cleaning up user...")
        try:
            db.session.delete(new_user)
            db.session.commit()
            print(f"✅ [REGISTER] User deleted from database")
        except Exception as e:
            print(f"❌ [REGISTER] Error deleting user: {str(e)}")
            db.session.rollback()
        
        print("="*80 + "\n")
        return jsonify({
            'success': False, 
            'message': 'Email verification service is currently unavailable. Please try again later or contact support.',
        }), 500

@api_bp.route('/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
    
    # Check if user exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return jsonify({
            'success': True, 
            'message': 'If an account with this email exists, password reset instructions have been sent.'
        })
    
    # Generate reset code
    reset_code = str(random.randint(100000, 999999))
    
    # Store reset code (in a real app, you'd want to store this with expiration)
    user.verification_code = reset_code
    db.session.commit()
    
    # Send reset email
    if send_password_reset_email(email, reset_code):
        return jsonify({
            'success': True, 
            'message': 'If an account with this email exists, password reset instructions have been sent.'
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to send reset email. Please try again.'}), 500

def send_password_reset_email(email, reset_code):
    """Send password reset email to user using SendGrid"""
    try:
        if not SENDGRID_API_KEY:
            return send_password_reset_email_smtp(email, reset_code)
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🏨 Easy Hotel</h1>
                <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Password Reset Request</p>
            </div>
            
            <div style="background: white; padding: 40px; border: 1px solid #e0e0e0; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Reset Your Password</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    You have requested to reset your password for your Easy Hotel account.
                </p>
                
                <div style="background: #fff5f5; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0; border-left: 4px solid #ff6b6b;">
                    <p style="color: #333; margin: 0 0 10px 0; font-size: 14px;">Your password reset code is:</p>
                    <div style="font-size: 32px; font-weight: bold; color: #ff6b6b; letter-spacing: 3px; font-family: monospace;">
                        {reset_code}
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px; line-height: 1.6;">
                    Please enter this code in the app to reset your password. This code will expire in 1 hour.
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    If you didn't request this password reset, please ignore this email and your password will remain unchanged.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>© 2024 Easy Hotel. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Easy Hotel - Password Reset
        
        You have requested to reset your password.
        
        Your password reset code is: {reset_code}
        
        Please use this code to reset your password. This code will expire in 1 hour.
        
        If you did not request this password reset, please ignore this email and your password will remain unchanged.
        
        Best regards,
        Easy Hotel Team
        """
        
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=email,
            subject='Easy Hotel - Password Reset Code',
            html_content=html_content,
            plain_text_content=plain_content
        )
        
        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ [SENDGRID] Password reset email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ [SENDGRID] Password reset email error: {str(e)}")
        return send_password_reset_email_smtp(email, reset_code)

def send_password_reset_email_smtp(email, reset_code):
    """Fallback SMTP password reset email"""
    try:
        msg = MIMEText(f'''
        Easy Hotel - Password Reset
        
        You have requested to reset your password.
        
        Your password reset code is: {reset_code}
        
        Please use this code to reset your password. This code will expire in 1 hour.
        
        If you did not request this password reset, please ignore this email and your password will remain unchanged.
        
        Best regards,
        Easy Hotel Team
        ''')
        msg['Subject'] = 'Easy Hotel - Password Reset'
        msg['From'] = EMAIL_USERNAME
        msg['To'] = email
        
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USERNAME, [email], msg.as_string())
        
        return True
    except Exception as e:
        print(f"SMTP Password reset email error: {str(e)}")
        return False

def send_staff_verification_email(email, username, verification_code, password):
    """Send verification email to new staff member using SendGrid"""
    try:
        if not SENDGRID_API_KEY:
            return send_staff_verification_email_smtp(email, username, verification_code, password)
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">🏨 Easy Hotel</h1>
                <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Staff Account Created</p>
            </div>
            
            <div style="background: white; padding: 40px; border: 1px solid #e0e0e0; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Welcome to the Team, {username}!</h2>
                
                <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Your staff account has been created successfully. To complete your registration, please verify your email address.
                </p>
                
                <div style="background: #f0fff4; padding: 20px; border-radius: 8px; margin: 30px 0; border-left: 4px solid #2ecc71;">
                    <p style="color: #333; margin: 0 0 10px 0; font-size: 14px;">Your verification code is:</p>
                    <div style="font-size: 32px; font-weight: bold; color: #2ecc71; letter-spacing: 3px; font-family: monospace;">
                        {verification_code}
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Your Login Credentials</h3>
                    <p style="color: #666; margin: 5px 0;"><strong>Email:</strong> {email}</p>
                    <p style="color: #666; margin: 5px 0;"><strong>Password:</strong> {password}</p>
                    <p style="color: #e74c3c; font-size: 12px; margin-top: 15px;">
                        ⚠️ Please keep this information secure and do not share it with anyone.
                    </p>
                </div>
                
                <p style="color: #666; font-size: 14px; line-height: 1.6;">
                    Please provide the verification code to your administrator to activate your account.
                </p>
                
                <p style="color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    If you have any questions, please contact your administrator.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>© 2024 Easy Hotel Management Team. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Welcome to Easy Hotel Staff Team!
        
        Dear {username},
        
        Your staff account has been created successfully. To complete your registration, please verify your email address.
        
        Your verification code is: {verification_code}
        
        Please provide this code to your administrator to activate your account.
        
        Your login credentials (after verification):
        Email: {email}
        Password: {password}
        
        Please keep this information secure and do not share it with anyone.
        
        If you have any questions, please contact your administrator.
        
        Best regards,
        Easy Hotel Management Team
        """
        
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=email,
            subject='Easy Hotel - Staff Account Verification',
            html_content=html_content,
            plain_text_content=plain_content
        )
        
        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ [SENDGRID] Staff verification email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ [SENDGRID] Staff verification email error: {str(e)}")
        return send_staff_verification_email_smtp(email, username, verification_code, password)

def send_staff_verification_email_smtp(email, username, verification_code, password):
    """Fallback SMTP staff verification email"""
    try:
        msg = MIMEText(f'''
        Welcome to Easy Hotel Staff Team!
        
        Dear {username},
        
        Your staff account has been created successfully. To complete your registration, please verify your email address.
        
        Your verification code is: {verification_code}
        
        Please provide this code to your administrator to activate your account.
        
        Your login credentials (after verification):
        Email: {email}
        Password: {password}
        
        Please keep this information secure and do not share it with anyone.
        
        If you have any questions, please contact your administrator.
        
        Best regards,
        Easy Hotel Management Team
        ''')
        msg['Subject'] = 'Easy Hotel - Staff Account Verification'
        msg['From'] = EMAIL_USERNAME
        msg['To'] = email
        
        with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USERNAME, [email], msg.as_string())
        
        return True
    except Exception as e:
        print(f"SMTP Staff verification email error: {str(e)}")
        return False

@api_bp.route('/auth/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json()
    email = data.get('email')
    reset_code = data.get('reset_code')
    new_password = data.get('new_password')
    
    if not all([email, reset_code, new_password]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    # Find user with matching email and reset code
    user = User.query.filter_by(email=email, verification_code=reset_code).first()
    if not user:
        return jsonify({'success': False, 'message': 'Invalid reset code or email'}), 400
    
    # Update password and clear reset code
    user.set_password(new_password)
    user.verification_code = None
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Password reset successfully'
    })

# User Routes
@api_bp.route('/user/profile', methods=['GET'])
@token_required
def get_user_profile(current_user_id):
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'is_admin': user.is_admin,
            'is_staff': user.is_staff,
            'staff_role': user.staff_role,
            'staff_status': user.staff_status,
            'staff_shift': user.staff_shift,
            'created_at': user.created_at.isoformat(),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'home_address': user.home_address,
            'id_document_url': user.id_document_url
        }
    })

@api_bp.route('/user/profile', methods=['PUT'])
@token_required
def update_user_profile(current_user_id):
    from datetime import datetime
    import os
    from werkzeug.utils import secure_filename
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Check if request has file upload (multipart/form-data)
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
        
        # Handle ID document upload
        if 'id_document' in request.files:
            file = request.files['id_document']
            if file and file.filename:
                filename = secure_filename(f"id_{user.id}_{datetime.now().timestamp()}_{file.filename}")
                upload_folder = os.path.join('EasyHotelBooking', 'static', 'uploads', 'ids')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                user.id_document_url = f'/static/uploads/ids/{filename}'
    else:
        data = request.get_json()
    
    # Update basic fields
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'phone_number' in data:
        user.phone_number = data['phone_number']
    
    # Update personal information fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'birth_date' in data and data['birth_date']:
        try:
            user.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        except ValueError:
            pass
    if 'home_address' in data:
        user.home_address = data['home_address']
    
    # Handle password change
    if 'new_password' in data and 'current_password' in data:
        if user.check_password(data['current_password']):
            user.set_password(data['new_password'])
        else:
            return jsonify({'message': 'Current password is incorrect'}), 400
    
    db.session.commit()
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'is_admin': user.is_admin,
            'is_staff': user.is_staff,
            'staff_role': user.staff_role,
            'staff_status': user.staff_status,
            'staff_shift': user.staff_shift,
            'created_at': user.created_at.isoformat(),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'home_address': user.home_address,
            'id_document_url': user.id_document_url
        }
    })

# Room Routes
@api_bp.route('/rooms', methods=['GET'])
def get_rooms():
    from models import RoomSize, FloorPlan, AmenityDetail, AmenityMaster
    
    rooms = Room.query.all()
    rooms_data = []
    
    for room in rooms:
        # Get related data
        room_size = RoomSize.query.get(room.room_size_id) if room.room_size_id else None
        floor_plan = FloorPlan.query.get(room.floor_id) if room.floor_id else None
        
        # Get amenities for this room type
        amenities = []
        if room_size:
            amenity_details = AmenityDetail.query.filter_by(room_size_id=room_size.id).all()
            for detail in amenity_details:
                amenity = AmenityMaster.query.get(detail.amenity_id)
                if amenity:
                    amenities.append({
                        'id': amenity.id,
                        'name': amenity.name,
                        'icon_url': amenity.icon_url or '',
                        'description': amenity.description or ''
                    })
        
        # Calculate capacity with fallbacks
        max_adults = room_size.max_adults if room_size and room_size.max_adults else 2
        max_children = room_size.max_children if room_size and room_size.max_children else 1
        
        # Use legacy capacity field if available, otherwise calculate
        if room.capacity and room.capacity > 0:
            max_adults = room.capacity
            max_children = 0
        
        # Get room type name with fallback
        room_type_name = 'Standard'
        if room_size and room_size.room_type_name:
            room_type_name = room_size.room_type_name
        elif room.name:
            # Try to extract type from name (e.g., "Deluxe Room 101" -> "Deluxe")
            parts = room.name.split()
            if len(parts) > 1 and parts[0] not in ['Room', 'room']:
                room_type_name = parts[0]
        
        # Get all room images and convert to full URLs
        from flask import request
        base_url = request.host_url.rstrip('/')  # e.g., http://localhost:5000 or https://your-domain.com
        
        images = []
        for img in [room.image_1, room.image_2, room.image_3, room.image_4, room.image_5]:
            if img:
                # If it's a local path, convert to full URL
                if img.startswith('/static/'):
                    images.append(f"{base_url}{img}")
                else:
                    images.append(img)
        
        # Ensure we have at least one image
        primary_image = room.image_url or room.image_1 or room.image_2 or ''
        if primary_image and primary_image.startswith('/static/'):
            primary_image = f"{base_url}{primary_image}"
        
        # Convert individual image fields to full URLs
        def to_full_url(img_path):
            if img_path and img_path.startswith('/static/'):
                return f"{base_url}{img_path}"
            return img_path or ''
        
        room_dict = {
            'id': room.id,
            'room_number': room.room_number or '',
            'room_type_id': room.room_size_id or 0,
            'room_type_name': room_type_name,
            'floor_plan_id': room.floor_id or 0,
            'floor_name': floor_plan.floor_name if floor_plan else 'Ground Floor',
            'price_per_night': float(room.price_per_night) if room.price_per_night else 0.0,
            'max_adults': max_adults,
            'max_children': max_children,
            'status': room.status or 'available',
            'image_url': primary_image,
            'image_1': to_full_url(room.image_1),
            'image_2': to_full_url(room.image_2),
            'image_3': to_full_url(room.image_3),
            'image_4': to_full_url(room.image_4),
            'image_5': to_full_url(room.image_5),
            'images': images,  # Array of all images for carousel (already full URLs)
            'name': room.name or f'{room_type_name} Room {room.room_number}',
            'description': room.description or f'Comfortable {room_type_name.lower()} room with modern amenities',
            'capacity': max_adults + max_children,
            'amenities': amenities
        }
        rooms_data.append(room_dict)
    
    return jsonify({'data': rooms_data})

@api_bp.route('/admin/rooms', methods=['POST'])
@token_required
def create_room(current_user_id):
    print("\n🏨 [ROOM_CREATE] Starting room creation")
    print("="*50)
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        print(f"❌ [ROOM_CREATE] Unauthorized user: {user.username if user else 'None'}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    print(f"✅ [ROOM_CREATE] Admin user: {user.username}")
    
    # Get data from request (handle both JSON and form data)
    if request.is_json:
        data = request.get_json()
        print(f"📦 [ROOM_CREATE] Received JSON data: {data}")
    else:
        data = request.form.to_dict()
        print(f"📦 [ROOM_CREATE] Received form data: {data}")
    
    if not data:
        print("❌ [ROOM_CREATE] No data received")
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Extract fields (support both old and new formats)
    name = data.get('name')
    description = data.get('description', '')
    price_per_night = data.get('price_per_night')
    capacity = data.get('capacity', 2)
    image_url = data.get('image_url', '')
    status = data.get('status', 'available')
    
    # Handle file upload
    uploaded_file = None
    if 'image' in request.files:
        uploaded_file = request.files['image']
        print(f"📸 [ROOM_CREATE] Image file uploaded: {uploaded_file.filename}")
    
    # Generate room number if name is provided
    room_number = name
    if not room_number:
        # Fallback to old format
        room_number = data.get('room_number')
    
    # Validate required fields
    if not all([room_number, price_per_night]):
        print("❌ [ROOM_CREATE] Missing required fields")
        return jsonify({'success': False, 'message': 'Room name and price are required'}), 400
    
    # Check if room number already exists
    existing_room = Room.query.filter_by(room_number=room_number).first()
    if existing_room:
        print(f"❌ [ROOM_CREATE] Room already exists: {room_number}")
        return jsonify({'success': False, 'message': f'Room {room_number} already exists'}), 400
    
    try:
        price_per_night = float(price_per_night)
        capacity = int(capacity) if capacity else 2
    except ValueError:
        print("❌ [ROOM_CREATE] Invalid price or capacity format")
        return jsonify({'success': False, 'message': 'Invalid price or capacity format'}), 400
    
    print(f"🏨 [ROOM_CREATE] Creating room: {room_number}")
    print(f"   Price: ₱{price_per_night}")
    print(f"   Capacity: {capacity}")
    print(f"   Description: {description}")
    
    # Get or set default room size and floor
    room_size_id = data.get('room_size_id', 1)  # Default to Standard (ID 1)
    floor_id = data.get('floor_id', 1)  # Default to Ground Floor (ID 1)
    
    # Auto-assign floor based on room number if possible
    if room_number and len(room_number) >= 3 and room_number[0].isdigit():
        floor_digit = int(room_number[0])
        if floor_digit >= 1 and floor_digit <= 4:
            floor_id = floor_digit
    
    # Auto-assign room size based on capacity
    if capacity >= 4:
        room_size_id = 3  # Suite
    elif capacity >= 3:
        room_size_id = 2  # Deluxe
    else:
        room_size_id = 1  # Standard
    
    print(f"🏗️  [ROOM_CREATE] Using room_size_id: {room_size_id}, floor_id: {floor_id}")
    
    # Handle image upload
    final_image_url = image_url or 'https://via.placeholder.com/400x300'
    if uploaded_file and uploaded_file.filename:
        try:
            import os
            from werkzeug.utils import secure_filename
            
            # Create upload directory
            upload_dir = os.path.join('EasyHotelBooking', 'static', 'uploads', 'rooms')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate secure filename
            filename = secure_filename(uploaded_file.filename)
            timestamp = str(int(datetime.utcnow().timestamp()))
            filename = f"room_{timestamp}_{filename}"
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            uploaded_file.save(file_path)
            
            # Generate URL
            final_image_url = f"/static/uploads/rooms/{filename}"
            print(f"📸 [ROOM_CREATE] Image saved: {final_image_url}")
            
        except Exception as e:
            print(f"❌ [ROOM_CREATE] Image upload error: {str(e)}")
            # Continue with default image if upload fails
    
    # Create room with complete schema
    new_room = Room(
        room_number=room_number,
        room_size_id=room_size_id,
        floor_id=floor_id,
        name=name or room_number,
        description=description,
        price_per_night=price_per_night,
        capacity=capacity,
        status=status,
        image_url=final_image_url,
        image_1=final_image_url
    )
    
    try:
        db.session.add(new_room)
        db.session.commit()
        print(f"✅ [ROOM_CREATE] Room created successfully with ID: {new_room.id}")
    except Exception as e:
        print(f"❌ [ROOM_CREATE] Database error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    
    # Return room data in the format expected by Flutter
    room_data = {
        'id': new_room.id,
        'name': new_room.name or new_room.room_number,
        'room_number': new_room.room_number,
        'description': new_room.description or f'Comfortable room with modern amenities',
        'price_per_night': float(new_room.price_per_night),
        'capacity': new_room.capacity or 2,
        'status': new_room.status,
        'image_url': new_room.image_url,
        'images': [new_room.image_url] if new_room.image_url else [],
        'amenities': []
    }
    
    print(f"📤 [ROOM_CREATE] Returning room data: {room_data}")
    print("="*50 + "\n")
    
    return jsonify({
        'success': True,
        'message': 'Room created successfully',
        'room': room_data
    })

@api_bp.route('/admin/rooms/<int:room_id>', methods=['PUT'])
@token_required
def update_room(current_user_id, room_id):
    print(f"\n🏨 [ROOM_UPDATE] Updating room {room_id}")
    print("="*50)
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        print(f"❌ [ROOM_UPDATE] Unauthorized user: {user.username if user else 'None'}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        print(f"❌ [ROOM_UPDATE] Room not found: {room_id}")
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    print(f"✅ [ROOM_UPDATE] Admin user: {user.username}")
    print(f"🏨 [ROOM_UPDATE] Current room: {room.name or room.room_number}")
    
    # Get JSON data from request
    data = request.get_json()
    print(f"📦 [ROOM_UPDATE] Received data: {data}")
    
    # Update fields if provided (support both old and new formats)
    if 'name' in data:
        room.name = data['name']
        room.room_number = data['name']  # Keep room_number in sync
    elif 'room_number' in data:
        # Check if new room number already exists (excluding current room)
        existing_room = Room.query.filter_by(room_number=data['room_number']).filter(Room.id != room_id).first()
        if existing_room:
            print(f"❌ [ROOM_UPDATE] Room number already exists: {data['room_number']}")
            return jsonify({'success': False, 'message': f'Room number {data["room_number"]} already exists'}), 400
        room.room_number = data['room_number']
        room.name = data['room_number']
    
    if 'description' in data:
        room.description = data['description']
    
    if 'price_per_night' in data:
        try:
            room.price_per_night = float(data['price_per_night'])
        except ValueError:
            print("❌ [ROOM_UPDATE] Invalid price format")
            return jsonify({'success': False, 'message': 'Invalid price format'}), 400
    
    if 'capacity' in data:
        try:
            room.capacity = int(data['capacity'])
        except ValueError:
            print("❌ [ROOM_UPDATE] Invalid capacity format")
            return jsonify({'success': False, 'message': 'Invalid capacity format'}), 400
    
    if 'status' in data:
        room.status = data['status']
    
    if 'image_url' in data:
        room.image_url = data['image_url']
    
    try:
        db.session.commit()
        print(f"✅ [ROOM_UPDATE] Room updated successfully")
    except Exception as e:
        print(f"❌ [ROOM_UPDATE] Database error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
    
    # Return room data in the format expected by Flutter
    room_data = {
        'id': room.id,
        'name': room.name or room.room_number,
        'room_number': room.room_number,
        'description': room.description or f'Comfortable room with modern amenities',
        'price_per_night': float(room.price_per_night),
        'capacity': room.capacity or 2,
        'status': room.status,
        'image_url': room.image_url,
        'images': [room.image_url] if room.image_url else [],
        'amenities': []
    }
    
    print(f"📤 [ROOM_UPDATE] Returning room data: {room_data}")
    print("="*50 + "\n")
    
    return jsonify({
        'success': True,
        'message': 'Room updated successfully',
        'room': room_data
    })

@api_bp.route('/admin/rooms/<int:room_id>', methods=['DELETE'])
@token_required
def delete_room(current_user_id, room_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'success': False, 'message': 'Room not found'}), 404
    
    # Check if room has active bookings
    active_bookings = Booking.query.filter_by(room_id=room_id).filter(
        Booking.status.in_(['pending', 'confirmed'])
    ).count()
    
    if active_bookings > 0:
        return jsonify({'success': False, 'message': 'Cannot delete room with active bookings'}), 400
    
    db.session.delete(room)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Room deleted successfully'
    })

@api_bp.route('/check_availability', methods=['GET'])
def check_availability():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if not all([room_id, check_in, check_out]):
        return jsonify({'available': False, 'message': 'Missing parameters'}), 400
    
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'available': False, 'message': 'Invalid date format'}), 400
    
    # Check for overlapping bookings
    existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
        ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
        ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
        ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
    ).filter(Booking.status != 'cancelled').count()
    
    return jsonify({
        'available': existing_bookings == 0,
        'message': 'Room available' if existing_bookings == 0 else 'Room not available'
    })

@api_bp.route('/rooms/<int:room_id>/booked-dates', methods=['GET'])
def get_booked_dates(room_id):
    """Get all booked dates for a specific room"""
    try:
        from datetime import timedelta
        
        # Get all active bookings for this room
        bookings = Booking.query.filter_by(room_id=room_id).filter(
            Booking.status.in_(['pending', 'confirmed'])
        ).all()
        
        # Generate list of all booked dates
        # Include check-out date to prevent same-day check-in/check-out conflicts
        booked_dates = []
        for booking in bookings:
            current_date = booking.check_in_date
            while current_date <= booking.check_out_date:  # Changed < to <= to include check_out_date
                booked_dates.append(current_date.isoformat())
                current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'booked_dates': list(set(booked_dates))  # Remove duplicates
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching booked dates: {str(e)}'
        }), 500

@api_bp.route('/rooms/available', methods=['GET'])
def get_available_rooms():
    """Get available rooms for given date range"""
    try:
        from datetime import datetime
        
        check_in = request.args.get('check_in')
        check_out = request.args.get('check_out')
        
        if not check_in or not check_out:
            return jsonify({'success': False, 'message': 'Missing check_in or check_out dates'}), 400
        
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        # Get all rooms
        rooms = Room.query.all()
        available_rooms = []
        
        for room in rooms:
            # Check if room has any overlapping bookings
            overlapping = Booking.query.filter(
                Booking.room_id == room.id,
                Booking.status.in_(['pending', 'confirmed', 'checked_in']),
                Booking.check_out_date > check_in_date,
                Booking.check_in_date < check_out_date
            ).first()
            
            if not overlapping:
                available_rooms.append({
                    'id': room.id,
                    'name': room.name,
                    'room_number': room.room_number,
                    'price_per_night': room.price_per_night,
                    'capacity': room.capacity,
                    'description': room.description
                })
        
        return jsonify({'success': True, 'rooms': available_rooms})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/rooms/ratings', methods=['GET'])
def get_room_ratings():
    """Get average ratings for all rooms"""
    try:
        from sqlalchemy import func
        
        # Query to get average ratings per room
        room_ratings = (
            db.session.query(
                Room.id,
                Room.name,
                Room.room_number,
                func.avg(Rating.overall_rating).label('avg_overall'),
                func.avg(Rating.room_rating).label('avg_room'),
                func.avg(Rating.amenities_rating).label('avg_amenities'),
                func.avg(Rating.service_rating).label('avg_service'),
                func.count(Rating.id).label('rating_count')
            )
            .outerjoin(Booking, Room.id == Booking.room_id)
            .outerjoin(Rating, Booking.id == Rating.booking_id)
            .group_by(Room.id, Room.name, Room.room_number)
            .all()
        )
        
        ratings_data = []
        for room_rating in room_ratings:
            # Calculate overall average (if there are ratings)
            if room_rating.rating_count > 0:
                avg_overall = round(room_rating.avg_overall, 1)
                avg_room = round(room_rating.avg_room, 1)
                avg_amenities = round(room_rating.avg_amenities, 1)
                avg_service = round(room_rating.avg_service, 1)
            else:
                # Default ratings for rooms with no reviews
                avg_overall = 0.0
                avg_room = 0.0
                avg_amenities = 0.0
                avg_service = 0.0
            
            ratings_data.append({
                'room_id': room_rating.id,
                'room_name': room_rating.name,
                'room_number': room_rating.room_number,
                'average_rating': avg_overall,
                'room_rating': avg_room,
                'amenities_rating': avg_amenities,
                'service_rating': avg_service,
                'review_count': room_rating.rating_count,
                'stars': int(avg_overall) if avg_overall > 0 else 0  # For star display
            })
        
        return jsonify({
            'success': True,
            'ratings': ratings_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching room ratings: {str(e)}'
        }), 500

@api_bp.route('/rooms/<int:room_id>/ratings', methods=['GET'])
def get_room_specific_ratings(room_id):
    """Get detailed ratings for a specific room"""
    try:
        # Get room details
        room = Room.query.get_or_404(room_id)
        
        # Get all ratings for this room
        ratings = (
            db.session.query(Rating, User.username, Booking.check_in_date)
            .join(Booking, Rating.booking_id == Booking.id)
            .join(User, Rating.user_id == User.id)
            .filter(Booking.room_id == room_id)
            .order_by(Rating.created_at.desc())
            .all()
        )
        
        # Calculate averages
        if ratings:
            avg_overall = sum(r[0].overall_rating for r in ratings) / len(ratings)
            avg_room = sum(r[0].room_rating for r in ratings) / len(ratings)
            avg_amenities = sum(r[0].amenities_rating for r in ratings) / len(ratings)
            avg_service = sum(r[0].service_rating for r in ratings) / len(ratings)
        else:
            avg_overall = avg_room = avg_amenities = avg_service = 0.0
        
        # Format individual ratings
        ratings_list = []
        for rating, username, check_in_date in ratings:
            ratings_list.append({
                'id': rating.id,
                'username': username,
                'overall_rating': rating.overall_rating,
                'room_rating': rating.room_rating,
                'amenities_rating': rating.amenities_rating,
                'service_rating': rating.service_rating,
                'comment': rating.comment,
                'admin_reply': rating.admin_reply,
                'created_at': rating.created_at.isoformat() if rating.created_at else None,
                'stay_date': check_in_date.isoformat() if check_in_date else None
            })
        
        return jsonify({
            'success': True,
            'room': {
                'id': room.id,
                'name': room.name,
                'room_number': room.room_number
            },
            'averages': {
                'overall': round(avg_overall, 1),
                'room': round(avg_room, 1),
                'amenities': round(avg_amenities, 1),
                'service': round(avg_service, 1),
                'stars': int(avg_overall) if avg_overall > 0 else 0
            },
            'review_count': len(ratings),
            'ratings': ratings_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching room ratings: {str(e)}'
        }), 500

# Booking Routes
@api_bp.route('/bookings', methods=['GET'])
@token_required
def get_bookings(current_user_id):
    bookings = Booking.query.filter_by(user_id=current_user_id).all()
    return jsonify({
        'bookings': [booking.to_dict() for booking in bookings]
    })

@api_bp.route('/bookings', methods=['POST'])
@token_required
def create_booking(current_user_id):
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        room_id = data.get('room_id')
        check_in_str = data.get('check_in_date')
        check_out_str = data.get('check_out_date')
        guests = data.get('guests')
        amenities = data.get('amenities', [])
        
        # Validate required fields
        if not all([room_id, check_in_str, check_out_str, guests]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check maximum bookings per person (5 active bookings limit)
        active_bookings_count = Booking.query.filter_by(user_id=current_user_id).filter(
            Booking.status.in_(['pending', 'confirmed'])
        ).count()
        
        if active_bookings_count >= 5:
            return jsonify({
                'success': False, 
                'message': 'Maximum booking limit reached. You can have up to 5 active bookings at a time.'
            }), 400
        
        # Parse dates
        try:
            check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError as e:
            return jsonify({'success': False, 'message': f'Invalid date format: {str(e)}'}), 400
        
        # Get room
        room = Room.query.get(room_id)
        if not room:
            return jsonify({'success': False, 'message': 'Room not found'}), 404
        
        # Check availability
        existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
            ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
            ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
            ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
        ).filter(Booking.status != 'cancelled').count()
        
        if existing_bookings > 0:
            return jsonify({'success': False, 'message': 'Room not available for selected dates'}), 400
        
        # Calculate total price
        days = (check_out_date - check_in_date).days
        if days <= 0:
            return jsonify({'success': False, 'message': 'Check-out date must be after check-in date'}), 400
        
        total_price = room.price_per_night * days
        
        # Add amenities cost (only if amenities list is not empty)
        if amenities and isinstance(amenities, list):
            for amenity_data in amenities:
                if isinstance(amenity_data, dict) and 'id' in amenity_data:
                    amenity = Amenity.query.get(amenity_data['id'])
                    if amenity:
                        quantity = amenity_data.get('quantity', 1)
                        total_price += amenity.price * quantity
        
        # Create booking
        booking = Booking(
            user_id=current_user_id,
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            total_price=total_price,
            status='pending'
        )
        
        db.session.add(booking)
        db.session.flush()
        
        # Add amenities (only if amenities list is not empty)
        if amenities and isinstance(amenities, list):
            for amenity_data in amenities:
                if isinstance(amenity_data, dict) and 'id' in amenity_data:
                    booking_amenity = BookingAmenity(
                        booking_id=booking.id,
                        amenity_id=amenity_data['id'],
                        quantity=amenity_data.get('quantity', 1)
                    )
                    db.session.add(booking_amenity)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'booking': booking.to_dict(),
            'message': 'Booking created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating booking: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating booking: {str(e)}'
        }), 500

@api_bp.route('/bookings/<int:booking_id>/refund-eligibility', methods=['GET'])
@api_bp.route('/bookings/<int:booking_id>/refund-eligibility', methods=['GET'])
@token_required
def check_refund_eligibility(current_user_id, booking_id):
    """Check if a booking is eligible for refund"""
    from datetime import datetime, timedelta
    
    booking = Booking.query.get(booking_id)
    if not booking or booking.user_id != current_user_id:
        return jsonify({'message': 'Booking not found'}), 404
    
    # Calculate time until check-in
    now = datetime.utcnow()
    check_in_datetime = datetime.combine(booking.check_in_date, datetime.min.time())
    time_until_checkin = check_in_datetime - now
    hours_until_checkin = time_until_checkin.total_seconds() / 3600
    
    # Check if more than 24 hours before check-in
    is_refundable = hours_until_checkin > 24
    refund_amount = 0.0
    refund_percentage = 0
    
    if is_refundable and booking.paid_amount:
        refund_amount = booking.paid_amount
        refund_percentage = 100
    
    cancellation_deadline = check_in_datetime - timedelta(hours=24)
    
    return jsonify({
        'refund_eligible': is_refundable,
        'refund_amount': refund_amount,
        'refund_percentage': refund_percentage,
        'hours_until_checkin': round(hours_until_checkin, 2),
        'cancellation_deadline': cancellation_deadline.isoformat(),
        'check_in_date': booking.check_in_date.isoformat(),
        'booking_status': booking.status,
        'paid_amount': booking.paid_amount or 0.0,
        'policy': {
            'free_cancellation_hours': 24,
            'description': 'Free cancellation up to 24 hours before check-in'
        }
    })

@api_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@token_required
def cancel_booking(current_user_id, booking_id):
    from datetime import datetime, timedelta
    
    booking = Booking.query.get(booking_id)
    if not booking or booking.user_id != current_user_id:
        return jsonify({'message': 'Booking not found'}), 404
    
    # Check if booking is already cancelled
    if booking.status == 'cancelled':
        return jsonify({'message': 'Booking is already cancelled'}), 400
    
    data = request.get_json()
    reason = data.get('reason')
    
    if not reason:
        return jsonify({'message': 'Cancellation reason is required'}), 400
    
    # Calculate time until check-in
    now = datetime.utcnow()
    check_in_datetime = datetime.combine(booking.check_in_date, datetime.min.time())
    time_until_checkin = check_in_datetime - now
    hours_until_checkin = time_until_checkin.total_seconds() / 3600
    
    # Debug logging
    print(f"\n🔍 [CANCEL DEBUG] Booking #{booking_id}")
    print(f"   Now (UTC): {now}")
    print(f"   Check-in date: {booking.check_in_date}")
    print(f"   Check-in datetime: {check_in_datetime}")
    print(f"   Hours until check-in: {hours_until_checkin:.2f}")
    print(f"   Paid amount: {booking.paid_amount}")
    print(f"   Paid amount type: {type(booking.paid_amount)}")
    print(f"   Paid amount is None: {booking.paid_amount is None}")
    print(f"   Paid amount > 0: {booking.paid_amount > 0 if booking.paid_amount is not None else False}")
    
    # Check if more than 24 hours before check-in (refund policy)
    is_refundable = hours_until_checkin > 24
    refund_amount = 0.0
    refund_percentage = 0
    
    print(f"   Is refundable (>24h): {is_refundable}")
    
    if is_refundable and booking.paid_amount is not None and booking.paid_amount > 0:
        # Full refund if more than 24 hours before check-in
        refund_amount = float(booking.paid_amount)
        refund_percentage = 100
        print(f"   ✅ Refund eligible: ₱{refund_amount}")
    else:
        print(f"   ❌ Not eligible:")
        if not is_refundable:
            print(f"      - Not refundable (hours: {hours_until_checkin:.2f})")
        if booking.paid_amount is None or booking.paid_amount <= 0:
            print(f"      - No payment (paid_amount: {booking.paid_amount})")
    
    # Calculate time since booking was created (for info)
    booking_age = now - booking.created_at
    hours_since_booking = booking_age.total_seconds() / 3600
    
    # Update booking status
    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancelled_by = 'user'
    
    db.session.commit()
    
    return jsonify({
        'booking': booking.to_dict(),
        'message': 'Booking cancelled successfully',
        'refund_eligible': is_refundable,
        'refund_amount': refund_amount,
        'refund_percentage': refund_percentage,
        'hours_until_checkin': round(hours_until_checkin, 2),
        'hours_since_booking': round(hours_since_booking, 2),
        'cancellation_deadline': (check_in_datetime - timedelta(hours=24)).isoformat()
    })

# Admin Routes
@api_bp.route('/admin/bookings/all', methods=['GET'])
@token_required
def get_all_bookings(current_user_id):
    """Get all bookings for admin"""
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        bookings_data = []
        
        for booking in bookings:
            guest = User.query.get(booking.user_id)
            room = Room.query.get(booking.room_id)
            
            bookings_data.append({
                'id': booking.id,
                'user_id': booking.user_id,
                'guest_name': guest.username if guest else 'Unknown',
                'guest_email': guest.email if guest else '',
                'room_id': booking.room_id,
                'room_number': room.room_number if room else 'N/A',
                'room_type': room.name if room else 'N/A',
                'check_in': booking.check_in_date.strftime('%Y-%m-%d') if booking.check_in_date else None,
                'check_out': booking.check_out_date.strftime('%Y-%m-%d') if booking.check_out_date else None,
                'guests': booking.guests or 0,
                'total_price': float(booking.total_price) if booking.total_price else 0.0,
                'paid_amount': float(booking.paid_amount) if booking.paid_amount else 0.0,
                'status': booking.status or 'pending',
                'payment_status': booking.payment_status or 'pending',
                'created_at': booking.created_at.strftime('%Y-%m-%dT%H:%M:%S') if booking.created_at else None,
            })
        
        return jsonify({'success': True, 'bookings': bookings_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/bookings/pending', methods=['GET'])
@token_required
def get_pending_bookings(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    bookings = Booking.query.filter_by(status='pending').all()
    return jsonify({
        'bookings': [booking.to_dict() for booking in bookings]
    })

@api_bp.route('/admin/bookings/<int:booking_id>/verify', methods=['POST'])
@token_required
def verify_booking(current_user_id, booking_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'message': 'Booking not found'}), 404
    
    data = request.get_json()
    action = data.get('action')
    reason = data.get('reason')
    
    if action == 'confirm':
        booking.status = 'confirmed'
        message = 'Booking confirmed successfully'
    elif action == 'cancel':
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by = 'admin'
        booking.cancelled_at = datetime.utcnow()
        message = 'Booking cancelled successfully'
    elif action == 'checked_in' or action == 'check_in':
        booking.status = 'checked_in'
        booking.actual_check_in = datetime.utcnow()
        booking.checked_in_by = current_user_id
        message = 'Guest checked in successfully'
    elif action == 'checked_out' or action == 'check_out':
        booking.status = 'checked_out'
        booking.actual_check_out = datetime.utcnow()
        booking.checked_out_by = current_user_id
        message = 'Guest checked out successfully'
    else:
        return jsonify({'message': 'Invalid action'}), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'booking': booking.to_dict(),
        'message': message
    })

# Staff Routes
@api_bp.route('/staff/attendance', methods=['POST'])
@token_required
def staff_attendance(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_staff:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            verify_id = data.get('verify_id')
            action = data.get('action')
        else:
            verify_id = request.form.get('verify_id')
            action = request.form.get('action')
        
        if not verify_id or not action:
            return jsonify({'success': False, 'message': 'Missing verify_id or action'}), 400
        
        # Simple verification - in real app, you'd verify the ID
        if verify_id != str(user.id):
            return jsonify({'success': False, 'message': 'Invalid verification ID'}), 400
        
        from datetime import datetime, date
        from models import Attendance
        
        today = date.today()
        
        # Get or create attendance record for today
        attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).first()
        
        if not attendance:
            attendance = Attendance(
                user_id=current_user_id,
                date=today
            )
            db.session.add(attendance)
        
        if action == 'clock_in':
            if attendance.clock_in:
                return jsonify({'success': False, 'message': 'Already clocked in today'}), 400
            
            attendance.clock_in = datetime.now().time()
            message = 'Clocked in successfully'
            
        elif action == 'clock_out':
            if not attendance.clock_in:
                return jsonify({'success': False, 'message': 'Must clock in first'}), 400
            
            if attendance.clock_out:
                return jsonify({'success': False, 'message': 'Already clocked out today'}), 400
            
            attendance.clock_out = datetime.now().time()
            message = 'Clocked out successfully'
        
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        # Handle image upload if present
        if 'id_image' in request.files:
            image_file = request.files['id_image']
            if image_file and image_file.filename:
                import os
                from werkzeug.utils import secure_filename
                
                filename = secure_filename(image_file.filename)
                timestamp = str(int(datetime.now().timestamp()))
                filename = f"{timestamp}_{filename}"
                
                upload_folder = os.path.join('static', 'uploads', 'attendance_ids')
                os.makedirs(upload_folder, exist_ok=True)
                
                file_path = os.path.join(upload_folder, filename)
                image_file.save(file_path)
                
                attendance.id_image = f"/static/uploads/attendance_ids/{filename}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'attendance': {
                'date': attendance.date.isoformat(),
                'clock_in': attendance.clock_in.isoformat() if attendance.clock_in else None,
                'clock_out': attendance.clock_out.isoformat() if attendance.clock_out else None,
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Admin Staff Management Routes
@api_bp.route('/admin/staff', methods=['GET'])
@token_required
def get_all_staff(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    staff_members = User.query.filter_by(is_staff=True, staff_status='active').all()
    
    staff_list = []
    for staff in staff_members:
        staff_list.append({
            'id': staff.id,
            'username': staff.username,
            'email': staff.email,
            'staff_role': staff.staff_role,
            'staff_shift': staff.staff_shift,
            'staff_status': staff.staff_status,
            'phone_number': staff.phone_number,
            'is_verified': staff.is_verified,
            'created_at': staff.created_at.isoformat() if staff.created_at else None,
            'salary_type': staff.salary_type if hasattr(staff, 'salary_type') else 'hourly',
            'base_salary': staff.base_salary if hasattr(staff, 'base_salary') else 0.0,
            'hourly_rate': staff.hourly_rate if hasattr(staff, 'hourly_rate') else 0.0,
            'overtime_rate': staff.overtime_rate if hasattr(staff, 'overtime_rate') else 0.0,
        })
    
    return jsonify({
        'success': True,
        'staff': staff_list,
        'total': len(staff_list)
    })

@api_bp.route('/admin/staff', methods=['POST'])
@token_required
def create_staff(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Validation
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    phone_number = data.get('phone_number')
    staff_role = data.get('staff_role')
    staff_shift = data.get('staff_shift')
    
    if not all([username, email, password, phone_number, staff_role]):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({'message': 'User already exists'}), 400
    
    # Generate verification code
    verification_code = str(random.randint(100000, 999999))
    
    # Create staff member with verification pending
    new_staff = User(
        username=username,
        email=email,
        phone_number=phone_number,
        is_staff=True,
        staff_role=staff_role,
        staff_shift=staff_shift,
        staff_status='active',
        is_verified=False,
        verification_code=verification_code
    )
    new_staff.set_password(password)
    
    db.session.add(new_staff)
    db.session.commit()
    
    # Send verification email
    if send_staff_verification_email(email, username, verification_code, password):
        return jsonify({
            'staff': new_staff.to_dict(),
            'message': 'Staff member created successfully. Verification email sent.',
            'requires_verification': True,
            'verification_code': verification_code  # For testing purposes
        })
    else:
        # If email fails, delete the staff and return error
        db.session.delete(new_staff)
        db.session.commit()
        return jsonify({'message': 'Failed to send verification email. Please try again.'}), 500

@api_bp.route('/admin/staff/<int:staff_id>', methods=['PUT'])
@token_required
def update_staff(current_user_id, staff_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    staff_member = User.query.get(staff_id)
    if not staff_member or not staff_member.is_staff:
        return jsonify({'message': 'Staff member not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'username' in data:
        staff_member.username = data['username']
    if 'email' in data:
        staff_member.email = data['email']
    if 'phone_number' in data:
        staff_member.phone_number = data['phone_number']
    if 'staff_role' in data:
        staff_member.staff_role = data['staff_role']
    if 'staff_shift' in data:
        staff_member.staff_shift = data['staff_shift']
    if 'staff_status' in data:
        staff_member.staff_status = data['staff_status']
    
    db.session.commit()
    
    return jsonify({
        'staff': staff_member.to_dict(),
        'message': 'Staff member updated successfully'
    })

@api_bp.route('/admin/staff/<int:staff_id>', methods=['DELETE'])
@token_required
def delete_staff(current_user_id, staff_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    staff_member = User.query.get(staff_id)
    if not staff_member or not staff_member.is_staff:
        return jsonify({'message': 'Staff member not found'}), 404
    
    db.session.delete(staff_member)
    db.session.commit()
    
    return jsonify({
        'message': 'Staff member deleted successfully'
    })

# Admin Attendance Management Routes
@api_bp.route('/admin/staff/<int:staff_id>/verify', methods=['POST'])
@token_required
def verify_staff(current_user_id, staff_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    verification_code = data.get('verification_code')
    
    if not verification_code:
        return jsonify({'message': 'Verification code is required'}), 400
    
    staff_member = User.query.get(staff_id)
    if not staff_member or not staff_member.is_staff:
        return jsonify({'message': 'Staff member not found'}), 404
    
    if staff_member.verification_code != verification_code:
        return jsonify({'message': 'Invalid verification code'}), 400
    
    # Verify the staff member
    staff_member.is_verified = True
    staff_member.verification_code = None
    db.session.commit()
    
    return jsonify({
        'staff': staff_member.to_dict(),
        'message': 'Staff member verified successfully'
    })

# Reports and Analytics Routes
@api_bp.route('/admin/reports/dashboard', methods=['GET'])
@token_required
def get_dashboard_reports(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        # Get date range (default to last 30 days)
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Total bookings
        total_bookings = Booking.query.count()
        pending_bookings = Booking.query.filter_by(status='pending').count()
        confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
        cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
        
        # Revenue calculations
        confirmed_bookings_list = Booking.query.filter_by(status='confirmed').all()
        total_revenue = sum(booking.total_price for booking in confirmed_bookings_list)
        
        # Recent bookings revenue (last 30 days)
        recent_bookings = Booking.query.filter(
            Booking.status == 'confirmed',
            Booking.created_at >= start_date
        ).all()
        recent_revenue = sum(booking.total_price for booking in recent_bookings)
        
        # Room statistics
        total_rooms = Room.query.count()
        
        # Occupancy rate calculation
        occupied_rooms = Booking.query.filter(
            Booking.status.in_(['confirmed', 'pending']),
            Booking.check_in_date <= end_date,
            Booking.check_out_date >= start_date
        ).count()
        
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Staff statistics
        total_staff = User.query.filter_by(is_staff=True).count()
        active_staff = User.query.filter_by(is_staff=True, staff_status='active').count()
        
        # Guest statistics
        total_guests = User.query.filter_by(is_staff=False, is_admin=False).count()
        
        # Average booking value
        avg_booking_value = total_revenue / confirmed_bookings if confirmed_bookings > 0 else 0
        
        return jsonify({
            'dashboard_stats': {
                'total_bookings': total_bookings,
                'pending_bookings': pending_bookings,
                'confirmed_bookings': confirmed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'total_revenue': total_revenue,
                'recent_revenue': recent_revenue,
                'total_rooms': total_rooms,
                'occupancy_rate': round(occupancy_rate, 2),
                'total_staff': total_staff,
                'active_staff': active_staff,
                'total_guests': total_guests,
                'avg_booking_value': round(avg_booking_value, 2)
            }
        })
    except Exception as e:
        return jsonify({'message': f'Error generating reports: {str(e)}'}), 500

@api_bp.route('/admin/reports/revenue', methods=['GET'])
@token_required
def get_revenue_report(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from datetime import datetime, timedelta
        
        # Get last 12 months of revenue data
        monthly_revenue = []
        current_date = datetime.now().date()
        
        for i in range(12):
            month_start = current_date.replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            month_bookings = Booking.query.filter(
                Booking.status == 'confirmed',
                Booking.created_at >= month_start,
                Booking.created_at < month_end
            ).all()
            
            month_revenue = sum(booking.total_price for booking in month_bookings)
            
            monthly_revenue.append({
                'month': month_start.strftime('%B %Y'),
                'revenue': month_revenue,
                'bookings_count': len(month_bookings)
            })
        
        # Room-wise revenue
        room_revenue = []
        rooms = Room.query.all()
        
        for room in rooms:
            room_bookings = Booking.query.filter_by(
                room_id=room.id,
                status='confirmed'
            ).all()
            
            room_total = sum(booking.total_price for booking in room_bookings)
            
            room_revenue.append({
                'room_name': room.name,
                'revenue': room_total,
                'bookings_count': len(room_bookings)
            })
        
        return jsonify({
            'monthly_revenue': monthly_revenue[::-1],  # Reverse to show oldest first
            'room_revenue': sorted(room_revenue, key=lambda x: x['revenue'], reverse=True)
        })
    except Exception as e:
        return jsonify({'message': f'Error generating revenue report: {str(e)}'}), 500

@api_bp.route('/admin/reports/occupancy', methods=['GET'])
@token_required
def get_occupancy_report(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from datetime import datetime, timedelta
        
        # Get last 30 days occupancy data
        occupancy_data = []
        current_date = datetime.now().date()
        
        for i in range(30):
            date = current_date - timedelta(days=i)
            
            # Count occupied rooms for this date
            occupied = Booking.query.filter(
                Booking.status.in_(['confirmed', 'pending']),
                Booking.check_in_date <= date,
                Booking.check_out_date > date
            ).count()
            
            total_rooms = Room.query.count()
            occupancy_rate = (occupied / total_rooms * 100) if total_rooms > 0 else 0
            
            occupancy_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'occupied_rooms': occupied,
                'total_rooms': total_rooms,
                'occupancy_rate': round(occupancy_rate, 2)
            })
        
        return jsonify({
            'occupancy_data': occupancy_data[::-1]  # Reverse to show oldest first
        })
    except Exception as e:
        return jsonify({'message': f'Error generating occupancy report: {str(e)}'}), 500

@api_bp.route('/admin/reports/guests', methods=['GET'])
@token_required
def get_guest_analytics(current_user_id):
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        # Guest registration trends
        from datetime import datetime, timedelta
        
        guest_trends = []
        current_date = datetime.now().date()
        
        for i in range(12):
            month_start = current_date.replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            
            new_guests = User.query.filter(
                User.is_staff == False,
                User.is_admin == False,
                User.created_at >= month_start,
                User.created_at < month_end
            ).count()
            
            guest_trends.append({
                'month': month_start.strftime('%B %Y'),
                'new_guests': new_guests
            })
        
        # Top guests by bookings
        top_guests = []
        guests = User.query.filter_by(is_staff=False, is_admin=False).all()
        
        for guest in guests:
            booking_count = Booking.query.filter_by(user_id=guest.id).count()
            total_spent = sum(
                booking.total_price 
                for booking in Booking.query.filter_by(user_id=guest.id, status='confirmed').all()
            )
            
            if booking_count > 0:
                top_guests.append({
                    'guest_name': guest.username,
                    'email': guest.email,
                    'total_bookings': booking_count,
                    'total_spent': total_spent
                })
        
        # Sort by total spent
        top_guests = sorted(top_guests, key=lambda x: x['total_spent'], reverse=True)[:10]
        
        return jsonify({
            'guest_trends': guest_trends[::-1],
            'top_guests': top_guests
        })
    except Exception as e:
        return jsonify({'message': f'Error generating guest analytics: {str(e)}'}), 500

# Notification Routes
@api_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user_id):
    print(f"\n📬 [API_ROUTES] Get notifications for user #{current_user_id}")
    notifications = Notification.query.filter_by(user_id=current_user_id).all()
    print(f"   Found {len(notifications)} notifications")
    
    result = []
    for n in notifications:
        print(f"   Notification #{n.id}:")
        print(f"      type={n.notification_type}")
        print(f"      related_id={n.related_id}")
        print(f"      action_url={n.action_url}")
        
        # Manually build the dict to ensure all fields are included
        notif_dict = {
            'id': n.id,
            'user_id': n.user_id,
            'title': n.title,
            'message': n.message,
            'notification_type': n.notification_type,
            'related_id': n.related_id,
            'action_url': n.action_url,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        }
        print(f"      Manual dict={notif_dict}")
        result.append(notif_dict)
    
    print(f"   ✅ Returning: {result}")
    return jsonify({'notifications': result})

@api_bp.route('/notifications/mark-all-read', methods=['POST'])
@token_required
def mark_notifications_read(current_user_id):
    notifications = Notification.query.filter_by(user_id=current_user_id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

# Payment Routes
@api_bp.route('/payment/methods', methods=['GET'])
def get_payment_methods():
    """Get available payment methods"""
    try:
        from models import PaymentMethod
        
        methods = PaymentMethod.query.filter_by(is_active=True).all()
        
        payment_methods = []
        for method in methods:
            payment_methods.append({
                'id': method.id,
                'name': method.name,
                'code': method.code,
                'is_online': method.is_online,
                'description': method.description,
                'icon_url': method.icon_url
            })
        
        return jsonify({
            'payment_methods': payment_methods
        })
        
    except Exception as e:
        return jsonify({'message': f'Error fetching payment methods: {str(e)}'}), 500

@api_bp.route('/payment/gcash/create', methods=['POST'])
@token_required
def create_gcash_payment(current_user_id):
    """Create GCash payment for booking"""
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        phone_number = data.get('phone_number')
        
        if not booking_id or not phone_number:
            return jsonify({'success': False, 'message': 'Missing booking_id or phone_number'}), 400
        
        # Verify booking belongs to user
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        print(f"\n💳 [GCASH PAYMENT] Creating payment for booking #{booking_id}")
        print(f"   User ID: {current_user_id}")
        print(f"   Booking status: {booking.status}")
        print(f"   Paid amount: ₱{booking.paid_amount}")
        print(f"   Payment status: {booking.payment_status}")
        
        # Check if booking already has a completed payment (exclude refunded payments)
        completed_payment = Payment.query.filter(
            Payment.booking_id == booking_id,
            Payment.payment_status == 'completed'
        ).first()
        
        # Also check if the booking itself is not refunded or cancelled
        if completed_payment and booking.payment_status not in ['refunded', 'pending']:
            print(f"   ❌ ERROR: Found completed payment #{completed_payment.id} - Amount: ₱{completed_payment.amount}")
            return jsonify({'success': False, 'message': 'Booking already paid'}), 400
        
        print(f"   ✅ No completed payment found, proceeding...")
        
        # Check for existing pending payment and delete it (allow retry)
        pending_payment = Payment.query.filter_by(
            booking_id=booking_id, 
            payment_status='pending'
        ).first()
        
        if pending_payment:
            # Delete the old pending payment to allow creating a new one
            db.session.delete(pending_payment)
            db.session.commit()
        
        # Calculate downpayment (30% of total price)
        downpayment_amount = booking.total_price * 0.30
        
        # Create GCash payment for downpayment only
        result = gcash_service.create_gcash_payment_intent(
            booking_id=booking_id,
            amount=downpayment_amount,
            user_phone=phone_number
        )
        
        if result['success']:
            # Use payment intent with attached payment method
            return jsonify({
                'success': True,
                'payment_id': result['payment_id'],
                'payment_intent_id': result['payment_intent_id'],
                'client_key': result['client_key'],
                'redirect_url': result.get('redirect_url'),
                'amount': downpayment_amount,
                'total_amount': booking.total_price,
                'remaining_balance': booking.total_price - downpayment_amount
            })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/<int:payment_id>/verify', methods=['POST'])
@token_required
def verify_payment(current_user_id, payment_id):
    """Verify payment status"""
    try:
        # Verify payment belongs to user
        payment = Payment.query.filter_by(id=payment_id).first()
        if not payment or payment.user_id != current_user_id:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
        
        result = gcash_service.verify_payment(payment_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/success', methods=['GET'])
def payment_success():
    """Payment success callback"""
    return """
    <html>
    <head>
        <title>Payment Successful</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
            .success-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }
            .success-icon { color: #4CAF50; font-size: 64px; margin-bottom: 20px; }
            .btn { background: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="success-card">
            <div class="success-icon">✅</div>
            <h2>Payment Successful!</h2>
            <p>Your hotel booking payment has been processed successfully.</p>
            <p>You will receive a confirmation email shortly.</p>
            <a href="http://192.168.100.159:53024" class="btn">Return to Hotel App</a>
        </div>
        <script>
            // Auto redirect after 5 seconds
            setTimeout(() => {
                window.location.href = 'http://192.168.100.159:53024';
            }, 5000);
        </script>
    </body>
    </html>
    """

@api_bp.route('/payment/cash/create', methods=['POST'])
@token_required
def create_cash_payment(current_user_id):
    """Create cash payment for booking"""
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({'success': False, 'message': 'Missing booking_id'}), 400
        
        # Verify booking belongs to user
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Check if booking already has a completed payment
        completed_payment = Payment.query.filter_by(
            booking_id=booking_id, 
            payment_status='completed'
        ).first()
        
        if completed_payment:
            return jsonify({'success': False, 'message': 'Booking already paid'}), 400
        
        # Check for existing pending payment and delete it (allow retry)
        pending_payment = Payment.query.filter_by(
            booking_id=booking_id, 
            payment_status='pending'
        ).first()
        
        if pending_payment:
            # Delete the old pending payment to allow creating a new one
            db.session.delete(pending_payment)
            db.session.commit()
        
        # Create cash payment record
        payment = Payment(
            booking_id=booking_id,
            user_id=current_user_id,
            amount=booking.total_price,
            payment_method='cash',
            payment_status='pending'  # Will be completed at check-in
        )
        
        db.session.add(payment)
        
        # Update booking status to confirmed (cash payment)
        booking.status = 'confirmed'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cash payment confirmed. Pay at check-in.',
            'payment_id': payment.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/demo-gcash', methods=['GET'])
def demo_gcash_payment():
    """Demo GCash payment page for testing"""
    amount = request.args.get('amount', '0')
    phone = request.args.get('phone', '')
    intent_id = request.args.get('intent_id', '')
    
    return f"""
    <html>
    <head>
        <title>Demo GCash Payment</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .payment-card {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }}
            .gcash-logo {{ color: #007bff; font-size: 32px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #28a745; text-align: center; margin: 20px 0; }}
            .btn {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; width: 100%; margin: 10px 0; font-size: 16px; }}
            .btn:hover {{ background: #0056b3; }}
            .btn-cancel {{ background: #dc3545; }}
            .btn-cancel:hover {{ background: #c82333; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="payment-card">
            <div class="gcash-logo">📱 GCash Demo</div>
            <div class="info">
                <strong>Demo Payment Mode</strong><br>
                This is a simulation of GCash payment for testing purposes.
            </div>
            <div class="amount">₱{amount}</div>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Merchant:</strong> Easy Hotel Booking</p>
            
            <button class="btn" onclick="simulateSuccess()">✅ Simulate Successful Payment</button>
            <button class="btn btn-cancel" onclick="simulateFailure()">❌ Simulate Failed Payment</button>
            
            <div class="info" style="margin-top: 20px; font-size: 14px;">
                <strong>Instructions:</strong><br>
                • Click "Simulate Successful Payment" to test successful payment flow<br>
                • Click "Simulate Failed Payment" to test error handling<br>
                • This will redirect back to your hotel app
            </div>
        </div>
        
        <script>
            function simulateSuccess() {{
                // Simulate payment processing delay
                document.querySelector('.payment-card').innerHTML = `
                    <div class="gcash-logo">📱 GCash Demo</div>
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 48px; color: #28a745;">✅</div>
                        <h3>Payment Successful!</h3>
                        <p>Redirecting back to hotel app...</p>
                    </div>
                `;
                
                setTimeout(() => {{
                    window.location.href = 'http://192.168.100.159:5000/api/payment/success';
                }}, 2000);
            }}
            
            function simulateFailure() {{
                document.querySelector('.payment-card').innerHTML = `
                    <div class="gcash-logo">📱 GCash Demo</div>
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 48px; color: #dc3545;">❌</div>
                        <h3>Payment Failed!</h3>
                        <p>Redirecting back to hotel app...</p>
                    </div>
                `;
                
                setTimeout(() => {{
                    window.location.href = 'http://192.168.100.159:5000/api/payment/failed';
                }}, 2000);
            }}
        </script>
    </body>
    </html>
    """

@api_bp.route('/payment/failed', methods=['GET'])
def payment_failed():
    """Payment failed callback"""
    return """
    <html>
    <head>
        <title>Payment Failed</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
            .error-card { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }
            .error-icon { color: #f44336; font-size: 64px; margin-bottom: 20px; }
            .btn { background: #2196F3; color: white; padding: 12px 24px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="error-card">
            <div class="error-icon">❌</div>
            <h2>Payment Failed</h2>
            <p>Your payment could not be processed at this time.</p>
            <p>Please try again or contact support if the problem persists.</p>
            <a href="http://192.168.100.159:53024" class="btn">Return to Hotel App</a>
        </div>
        <script>
            // Auto redirect after 10 seconds
            setTimeout(() => {
                window.location.href = 'http://192.168.100.159:53024';
            }, 10000);
        </script>
    </body>
    </html>
    """

@api_bp.route('/admin/payments', methods=['GET'])
@token_required
def get_all_payments(current_user_id):
    """Get all payments (admin only)"""
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        from models import Payment
        
        payments = Payment.query.order_by(Payment.created_at.desc()).all()
        
        payment_list = []
        for payment in payments:
            payment_list.append({
                'id': payment.id,
                'booking_id': payment.booking_id,
                'user_id': payment.user_id,
                'amount': payment.amount,
                'payment_method': payment.payment_method,
                'payment_status': payment.payment_status,
                'gcash_phone_number': payment.gcash_phone_number,
                'created_at': payment.created_at.isoformat(),
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
                'user_name': payment.user.username if payment.user else 'Unknown',
                'booking_room': payment.booking.room.name if payment.booking and payment.booking.room else 'Unknown'
            })
        
        return jsonify({
            'payments': payment_list,
            'total_payments': len(payment_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error fetching payments: {str(e)}'}), 500

@api_bp.route('/admin/payments/all', methods=['GET'])
@token_required
def get_all_payments_detailed(current_user_id):
    """Get all payments with booking details (admin only)"""
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        from models import Payment
        
        payments = Payment.query.order_by(Payment.created_at.desc()).all()
        
        payment_list = []
        for payment in payments:
            booking = payment.booking
            guest = payment.user
            
            # Calculate due amount
            due_amount = 0
            if booking:
                due_amount = max(0, booking.total_price - (booking.paid_amount or 0))
            
            payment_list.append({
                'id': payment.id,
                'booking_id': payment.booking_id,
                'user_id': payment.user_id,
                'guest_name': guest.username if guest else 'Unknown',
                'guest_email': guest.email if guest else '',
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'payment_status': payment.payment_status,
                'payment_type': booking.payment_type if booking else 'full_payment',
                'gcash_reference_number': payment.gcash_reference_number,
                'gcash_transaction_id': payment.gcash_transaction_id,
                'gcash_phone_number': payment.gcash_phone_number,
                'created_at': payment.created_at.isoformat(),
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
                'room_name': booking.room.name if booking and booking.room else 'N/A',
                'room_number': booking.room.room_number if booking and booking.room else 'N/A',
                'total_price': float(booking.total_price) if booking else 0.0,
                'paid_amount': float(booking.paid_amount) if booking else 0.0,
                'due_amount': float(due_amount),
            })
        
        return jsonify({
            'success': True,
            'payments': payment_list,
            'total_count': len(payment_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error fetching payments: {str(e)}'}), 500

@api_bp.route('/admin/payments/<int:payment_id>/verify', methods=['POST'])
@token_required
def admin_verify_payment(current_user_id, payment_id):
    """Verify/approve a payment (admin only)"""
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        from models import Payment
        
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
        
        data = request.get_json()
        approve = data.get('approve', True)
        
        if approve:
            # Debug logging
            print(f"\n💳 [PAYMENT APPROVAL] Payment #{payment_id}")
            print(f"   Payment amount: ₱{payment.amount}")
            print(f"   Booking ID: {payment.booking_id}")
            
            payment.payment_status = 'completed'
            payment.paid_at = datetime.utcnow()
            
            # Update booking payment status
            if payment.booking:
                old_paid_amount = payment.booking.paid_amount or 0
                payment.booking.paid_amount = old_paid_amount + payment.amount
                new_paid_amount = payment.booking.paid_amount
                
                print(f"   Booking paid_amount: ₱{old_paid_amount} → ₱{new_paid_amount}")
                
                payment.booking.update_payment_status()
                
                # If fully paid, confirm booking
                if payment.booking.paid_amount >= payment.booking.total_price:
                    payment.booking.status = 'confirmed'
                    print(f"   ✅ Booking fully paid! Status: confirmed")
                else:
                    print(f"   ⏳ Partial payment (₱{new_paid_amount}/₱{payment.booking.total_price})")
            
            message = 'Payment approved successfully'
            print(f"   ✅ {message}")
        else:
            payment.payment_status = 'failed'
            message = 'Payment rejected'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'payment': {
                'id': payment.id,
                'payment_status': payment.payment_status,
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error verifying payment: {str(e)}'}), 500

# Role-Based Feature API Routes

# 1. Front Desk Operations
@api_bp.route('/staff/checkin/<int:booking_id>', methods=['POST'])
@token_required
def process_checkin(current_user_id, booking_id):
    """Process guest check-in"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['front desk manager', 'receptionist']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.get_json()
        
        # Create check-in record
        checkin = CheckInOut(
            booking_id=booking_id,
            staff_id=current_user_id,
            action_type='check_in',
            notes=data.get('notes', ''),
            room_condition=data.get('room_condition', 'good')
        )
        
        # Update booking status
        booking.status = 'checked_in'
        
        # Update room status
        room_status = RoomStatus.query.filter_by(room_id=booking.room_id).first()
        if room_status:
            room_status.status = 'occupied'
        
        db.session.add(checkin)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Guest checked in successfully',
            'checkin_id': checkin.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/checkout/<int:booking_id>', methods=['POST'])
@token_required
def process_checkout(current_user_id, booking_id):
    """Process guest check-out"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['front desk manager', 'receptionist']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.get_json()
        
        # Create check-out record
        checkout = CheckInOut(
            booking_id=booking_id,
            staff_id=current_user_id,
            action_type='check_out',
            notes=data.get('notes', ''),
            room_condition=data.get('room_condition', 'good')
        )
        
        # Update booking status
        booking.status = 'checked_out'
        
        # Update room status to dirty (needs cleaning)
        room_status = RoomStatus.query.filter_by(room_id=booking.room_id).first()
        if not room_status:
            room_status = RoomStatus(room_id=booking.room_id, status='dirty')
            db.session.add(room_status)
        else:
            room_status.status = 'dirty'
        
        db.session.add(checkout)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Guest checked out successfully',
            'checkout_id': checkout.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/front-desk/bookings', methods=['GET'])
@token_required
def get_front_desk_bookings(current_user_id):
    """Get bookings for front desk operations"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['front desk manager', 'receptionist']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        # Get today's check-ins and check-outs
        today = datetime.now().date()
        
        checkins_today = Booking.query.filter(
            Booking.check_in_date == today,
            Booking.status.in_(['confirmed', 'pending'])
        ).all()
        
        checkouts_today = Booking.query.filter(
            Booking.check_out_date == today,
            Booking.status == 'checked_in'
        ).all()
        
        return jsonify({
            'checkins_today': [booking.to_dict() for booking in checkins_today],
            'checkouts_today': [booking.to_dict() for booking in checkouts_today]
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# 2. Housekeeping Management
@api_bp.route('/staff/housekeeping/rooms', methods=['GET'])
@token_required
def get_housekeeping_rooms(current_user_id):
    """Get room status for housekeeping"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['housekeeping supervisor', 'housekeeper']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        rooms = Room.query.all()
        room_data = []
        
        for room in rooms:
            status = RoomStatus.query.filter_by(room_id=room.id).first()
            room_info = room.to_dict()
            room_info['status'] = status.status if status else 'clean'
            room_info['last_cleaned'] = status.last_cleaned.isoformat() if status and status.last_cleaned else None
            room_info['inspection_status'] = status.inspection_status if status else 'pending'
            room_data.append(room_info)
        
        return jsonify({'rooms': room_data})
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/staff/housekeeping/clean-room/<int:room_id>', methods=['POST'])
@token_required
def mark_room_cleaned(current_user_id, room_id):
    """Mark room as cleaned"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['housekeeping supervisor', 'housekeeper']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        # Update or create room status
        room_status = RoomStatus.query.filter_by(room_id=room_id).first()
        if not room_status:
            room_status = RoomStatus(room_id=room_id)
            db.session.add(room_status)
        
        room_status.status = 'clean'
        room_status.last_cleaned = datetime.utcnow()
        room_status.cleaned_by = current_user_id
        room_status.notes = data.get('notes', '')
        room_status.inspection_status = 'pending'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room marked as cleaned'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/housekeeping/tasks', methods=['GET'])
@token_required
def get_cleaning_tasks(current_user_id):
    """Get cleaning tasks for staff member"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() not in ['housekeeping supervisor', 'housekeeper']:
            return jsonify({'message': 'Unauthorized'}), 403
        
        tasks = CleaningTask.query.filter_by(assigned_to=current_user_id).filter(
            CleaningTask.status.in_(['pending', 'in_progress'])
        ).all()
        
        task_data = []
        for task in tasks:
            task_info = {
                'id': task.id,
                'room_name': task.room.name,
                'task_type': task.task_type,
                'priority': task.priority,
                'status': task.status,
                'scheduled_time': task.scheduled_time.isoformat(),
                'estimated_duration': task.estimated_duration,
                'notes': task.notes
            }
            task_data.append(task_info)
        
        return jsonify({'tasks': task_data})
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# 3. Security System
@api_bp.route('/staff/security/start-patrol', methods=['POST'])
@token_required
def start_security_patrol(current_user_id):
    """Start a security patrol"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'security guard':
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        patrol = SecurityPatrol(
            guard_id=current_user_id,
            patrol_route=data.get('patrol_route', 'general'),
            start_time=datetime.utcnow()
        )
        
        db.session.add(patrol)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'patrol_id': patrol.id,
            'message': 'Patrol started'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/security/report-incident', methods=['POST'])
@token_required
def report_security_incident(current_user_id):
    """Report a security incident"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        
        incident = SecurityIncident(
            reported_by=current_user_id,
            incident_type=data.get('incident_type'),
            severity=data.get('severity'),
            location=data.get('location'),
            description=data.get('description'),
            incident_time=datetime.fromisoformat(data.get('incident_time', datetime.utcnow().isoformat()))
        )
        
        db.session.add(incident)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'incident_id': incident.id,
            'message': 'Incident reported successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# 4. Maintenance Module
@api_bp.route('/staff/maintenance/work-orders', methods=['GET'])
@token_required
def get_work_orders(current_user_id):
    """Get work orders for maintenance staff"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'maintenance':
            return jsonify({'message': 'Unauthorized'}), 403
        
        work_orders = WorkOrder.query.filter_by(assigned_to=current_user_id).filter(
            WorkOrder.status.in_(['assigned', 'in_progress'])
        ).all()
        
        order_data = []
        for order in work_orders:
            order_info = {
                'id': order.id,
                'title': order.title,
                'description': order.description,
                'room_name': order.room.name if order.room else None,
                'location': order.location,
                'category': order.category,
                'priority': order.priority,
                'status': order.status,
                'estimated_hours': order.estimated_hours,
                'scheduled_date': order.scheduled_date.isoformat() if order.scheduled_date else None
            }
            order_data.append(order_info)
        
        return jsonify({'work_orders': order_data})
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/staff/maintenance/work-order/<int:order_id>/update', methods=['POST'])
@token_required
def update_work_order(current_user_id, order_id):
    """Update work order status"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'maintenance':
            return jsonify({'message': 'Unauthorized'}), 403
        
        work_order = WorkOrder.query.get(order_id)
        if not work_order or work_order.assigned_to != current_user_id:
            return jsonify({'message': 'Work order not found'}), 404
        
        data = request.get_json()
        
        if 'status' in data:
            work_order.status = data['status']
            if data['status'] == 'in_progress' and not work_order.started_date:
                work_order.started_date = datetime.utcnow()
            elif data['status'] == 'completed':
                work_order.completed_date = datetime.utcnow()
        
        if 'actual_hours' in data:
            work_order.actual_hours = data['actual_hours']
        if 'actual_cost' in data:
            work_order.actual_cost = data['actual_cost']
        if 'notes' in data:
            work_order.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Work order updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Staff Reservations Management
@api_bp.route('/staff/reservations/all', methods=['GET'])
@token_required
def get_all_reservations(current_user_id):
    """Get all reservations for staff management"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        # Get all bookings with user and room information
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        
        booking_data = []
        for booking in bookings:
            booking_info = booking.to_dict()
            booking_data.append(booking_info)
        
        return jsonify({
            'bookings': booking_data,
            'total_count': len(booking_data)
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@api_bp.route('/staff/reservations/confirm/<int:booking_id>', methods=['POST'])
@token_required
def confirm_reservation(current_user_id, booking_id):
    """Confirm a pending reservation"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        if booking.status != 'pending':
            return jsonify({'message': 'Booking is not pending'}), 400
        
        booking.status = 'confirmed'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reservation confirmed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/reservations/cancel/<int:booking_id>', methods=['POST'])
@token_required
def cancel_reservation(current_user_id, booking_id):
    """Cancel a reservation"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'message': 'Unauthorized'}), 403
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.get_json()
        reason = data.get('reason', 'Cancelled by staff')
        
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by = 'staff'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reservation cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# 5. Manager Dashboard
@api_bp.route('/staff/manager/overview', methods=['GET'])
@token_required
def get_manager_overview(current_user_id):
    """Get manager dashboard overview"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff or user.staff_role.lower() != 'manager':
            return jsonify({'message': 'Unauthorized'}), 403
        
        today = datetime.now().date()
        
        # Get today's statistics
        checkins_today = CheckInOut.query.filter(
            CheckInOut.action_type == 'check_in',
            db.func.date(CheckInOut.action_time) == today
        ).count()
        
        checkouts_today = CheckInOut.query.filter(
            CheckInOut.action_type == 'check_out',
            db.func.date(CheckInOut.action_time) == today
        ).count()
        
        open_work_orders = WorkOrder.query.filter(
            WorkOrder.status.in_(['open', 'assigned', 'in_progress'])
        ).count()
        
        security_incidents_today = SecurityIncident.query.filter(
            db.func.date(SecurityIncident.created_at) == today
        ).count()
        
        # Staff attendance today
        total_staff = User.query.filter_by(is_staff=True, staff_status='active').count()
        clocked_in_today = Attendance.query.filter(
            Attendance.date == today,
            Attendance.clock_in.isnot(None)
        ).count()
        
        attendance_rate = (clocked_in_today / total_staff * 100) if total_staff > 0 else 0
        
        return jsonify({
            'overview': {
                'checkins_today': checkins_today,
                'checkouts_today': checkouts_today,
                'open_work_orders': open_work_orders,
                'security_incidents_today': security_incidents_today,
                'staff_attendance_rate': round(attendance_rate, 1),
                'total_staff': total_staff,
                'clocked_in_staff': clocked_in_today
            }
        })
        
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Helper method to add to_dict methods to models
def add_to_dict_methods():
    def user_to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'is_admin': self.is_admin,
            'is_staff': self.is_staff,
            'staff_role': self.staff_role,
            'staff_status': self.staff_status,
            'staff_shift': self.staff_shift,
            'is_verified': self.is_verified,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None
        }
    
    def room_to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price_per_night': self.price_per_night,
            'capacity': self.capacity,
            'image_url': self.image_url
        }
    
    def booking_to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'check_in_date': self.check_in_date.strftime('%Y-%m-%d') if self.check_in_date else None,
            'check_out_date': self.check_out_date.strftime('%Y-%m-%d') if self.check_out_date else None,
            'guests': self.guests,
            'total_price': self.total_price,
            'paid_amount': self.paid_amount,
            'payment_status': self.payment_status,
            'status': self.status,
            'cancellation_reason': self.cancellation_reason,
            'cancelled_by': self.cancelled_by,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None,
            'room': self.room.to_dict() if self.room else None,
            'user': self.user.to_dict() if self.user else None
        }
    
    def notification_to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S') if self.created_at else None
        }
    
    # Add methods to models
    User.to_dict = user_to_dict
    Room.to_dict = room_to_dict
    Booking.to_dict = booking_to_dict
    Notification.to_dict = notification_to_dict

# Add to_dict methods
add_to_dict_methods()

# ============================================
# RFID CARD MANAGEMENT API ROUTES
# ============================================

@api_bp.route('/rfid/register', methods=['POST'])
@token_required
def register_rfid_card(current_user_id):
    """Register a new RFID card for a user"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        data = request.get_json()
        
        card_uid = data.get('card_uid')
        target_user_id = data.get('user_id')
        card_type = data.get('card_type', 'staff_badge')  # staff_badge, room_key, access_card
        expiry_days = data.get('expiry_days', 365)
        
        if not card_uid or not target_user_id:
            return jsonify({'success': False, 'message': 'Missing card_uid or user_id'}), 400
        
        # Check if card already exists
        existing_card = RFIDCard.query.filter_by(card_uid=card_uid).first()
        if existing_card:
            return jsonify({'success': False, 'message': 'RFID card already registered'}), 400
        
        # Check if user exists
        target_user = User.query.get(target_user_id)
        if not target_user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Create new RFID card
        from datetime import timedelta
        new_card = RFIDCard(
            card_uid=card_uid,
            user_id=target_user_id,
            card_type=card_type,
            is_active=True,
            issued_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=expiry_days),
            notes=data.get('notes', '')
        )
        
        db.session.add(new_card)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'RFID card registered successfully',
            'card': {
                'id': new_card.id,
                'card_uid': new_card.card_uid,
                'user_id': new_card.user_id,
                'user_name': target_user.username,
                'card_type': new_card.card_type,
                'issued_date': new_card.issued_date.isoformat(),
                'expiry_date': new_card.expiry_date.isoformat() if new_card.expiry_date else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/verify', methods=['POST'])
@token_required
def verify_rfid_card(current_user_id):
    """Verify RFID card and log access"""
    try:
        from models import RFIDCard, RFIDAccessLog
        data = request.get_json()
        
        card_uid = data.get('card_uid')
        access_type = data.get('access_type', 'attendance')  # attendance, room_access, checkpoint
        access_location = data.get('access_location', 'unknown')
        
        if not card_uid:
            return jsonify({'success': False, 'message': 'Missing card_uid'}), 400
        
        # Find RFID card
        rfid_card = RFIDCard.query.filter_by(card_uid=card_uid).first()
        
        if not rfid_card:
            # Log failed access attempt
            access_log = RFIDAccessLog(
                rfid_card_id=0,  # Unknown card
                user_id=current_user_id,
                access_type=access_type,
                access_location=access_location,
                access_granted=False,
                denial_reason='Card not registered'
            )
            db.session.add(access_log)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'access_granted': False,
                'message': 'RFID card not registered'
            }), 404
        
        # Check if card is active
        if not rfid_card.is_active:
            access_log = RFIDAccessLog(
                rfid_card_id=rfid_card.id,
                user_id=rfid_card.user_id,
                access_type=access_type,
                access_location=access_location,
                access_granted=False,
                denial_reason='Card is inactive'
            )
            db.session.add(access_log)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'access_granted': False,
                'message': 'RFID card is inactive'
            }), 403
        
        # Check if card is expired
        if rfid_card.expiry_date and rfid_card.expiry_date < datetime.utcnow():
            access_log = RFIDAccessLog(
                rfid_card_id=rfid_card.id,
                user_id=rfid_card.user_id,
                access_type=access_type,
                access_location=access_location,
                access_granted=False,
                denial_reason='Card expired'
            )
            db.session.add(access_log)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'access_granted': False,
                'message': 'RFID card has expired'
            }), 403
        
        # Access granted - log successful access
        access_log = RFIDAccessLog(
            rfid_card_id=rfid_card.id,
            user_id=rfid_card.user_id,
            access_type=access_type,
            access_location=access_location,
            access_granted=True
        )
        
        # Update last used time
        rfid_card.last_used = datetime.utcnow()
        
        db.session.add(access_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'access_granted': True,
            'message': 'Access granted',
            'user': {
                'id': rfid_card.user.id,
                'username': rfid_card.user.username,
                'email': rfid_card.user.email,
                'is_staff': rfid_card.user.is_staff,
                'staff_role': rfid_card.user.staff_role
            },
            'card': {
                'card_type': rfid_card.card_type,
                'issued_date': rfid_card.issued_date.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards', methods=['GET'])
@token_required
def get_all_rfid_cards(current_user_id):
    """Get all RFID cards (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        
        cards = RFIDCard.query.all()
        
        card_list = []
        for card in cards:
            card_list.append({
                'id': card.id,
                'card_uid': card.card_uid,
                'user_id': card.user_id,
                'user_name': card.user.username if card.user else 'Unknown',
                'card_type': card.card_type,
                'is_active': card.is_active,
                'issued_date': card.issued_date.isoformat(),
                'expiry_date': card.expiry_date.isoformat() if card.expiry_date else None,
                'last_used': card.last_used.isoformat() if card.last_used else None,
                'notes': card.notes
            })
        
        return jsonify({
            'cards': card_list,
            'total_cards': len(card_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards/user/<int:user_id>', methods=['GET'])
@token_required
def get_user_rfid_cards(current_user_id, user_id):
    """Get RFID cards for a specific user"""
    try:
        # Users can view their own cards, admins can view any
        user = User.query.get(current_user_id)
        if current_user_id != user_id and (not user or not user.is_admin):
            return jsonify({'message': 'Unauthorized'}), 403
        
        from models import RFIDCard
        
        cards = RFIDCard.query.filter_by(user_id=user_id).all()
        
        card_list = []
        for card in cards:
            card_list.append({
                'id': card.id,
                'card_uid': card.card_uid,
                'card_type': card.card_type,
                'is_active': card.is_active,
                'issued_date': card.issued_date.isoformat(),
                'expiry_date': card.expiry_date.isoformat() if card.expiry_date else None,
                'last_used': card.last_used.isoformat() if card.last_used else None
            })
        
        return jsonify({
            'cards': card_list,
            'total_cards': len(card_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards/<int:card_id>/deactivate', methods=['POST'])
@token_required
def deactivate_rfid_card(current_user_id, card_id):
    """Deactivate an RFID card (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        
        card = RFIDCard.query.get(card_id)
        if not card:
            return jsonify({'success': False, 'message': 'Card not found'}), 404
        
        card.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'RFID card deactivated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/cards/<int:card_id>/activate', methods=['POST'])
@token_required
def activate_rfid_card(current_user_id, card_id):
    """Activate an RFID card (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDCard
        
        card = RFIDCard.query.get(card_id)
        if not card:
            return jsonify({'success': False, 'message': 'Card not found'}), 404
        
        card.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'RFID card activated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/access-logs', methods=['GET'])
@token_required
def get_rfid_access_logs(current_user_id):
    """Get RFID access logs (admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin only'}), 403
        
        from models import RFIDAccessLog
        from datetime import timedelta
        
        # Get logs from last 30 days by default
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = RFIDAccessLog.query.filter(
            RFIDAccessLog.access_time >= start_date
        ).order_by(RFIDAccessLog.access_time.desc()).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'user_id': log.user_id,
                'user_name': log.user.username if log.user else 'Unknown',
                'card_uid': log.rfid_card.card_uid if log.rfid_card else 'Unknown',
                'access_type': log.access_type,
                'access_location': log.access_location,
                'access_time': log.access_time.isoformat(),
                'access_granted': log.access_granted,
                'denial_reason': log.denial_reason
            })
        
        return jsonify({
            'logs': log_list,
            'total_logs': len(log_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@api_bp.route('/rfid/access-logs/user/<int:user_id>', methods=['GET'])
@token_required
def get_user_rfid_access_logs(current_user_id, user_id):
    """Get RFID access logs for a specific user"""
    try:
        # Users can view their own logs, admins can view any
        user = User.query.get(current_user_id)
        if current_user_id != user_id and (not user or not user.is_admin):
            return jsonify({'message': 'Unauthorized'}), 403
        
        from models import RFIDAccessLog
        from datetime import timedelta
        
        # Get logs from last 30 days by default
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = RFIDAccessLog.query.filter(
            RFIDAccessLog.user_id == user_id,
            RFIDAccessLog.access_time >= start_date
        ).order_by(RFIDAccessLog.access_time.desc()).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'access_type': log.access_type,
                'access_location': log.access_location,
                'access_time': log.access_time.isoformat(),
                'access_granted': log.access_granted,
                'denial_reason': log.denial_reason
            })
        
        return jsonify({
            'logs': log_list,
            'total_logs': len(log_list)
        })
        
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ==================== ADMIN ATTENDANCE MANAGEMENT ====================

@api_bp.route('/admin/attendance', methods=['GET'])
@token_required
def get_all_attendance_records(current_user_id):
    """Get all attendance records with filters (Admin only)"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin access required'}), 403

        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        staff_id = request.args.get('staff_id')

        # Build query
        query = Attendance.query

        # Apply filters
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if staff_id:
            query = query.filter(Attendance.user_id == int(staff_id))

        # Get attendance records with staff info
        attendance_records = query.order_by(Attendance.date.desc(), Attendance.clock_in_time.desc()).all()

        attendance_list = []
        for record in attendance_records:
            staff = User.query.get(record.user_id)
            attendance_list.append({
                'id': record.id,
                'user_id': record.user_id,
                'staff_name': staff.username if staff else 'Unknown',
                'staff_role': staff.staff_role if staff else 'N/A',
                'date': record.date.isoformat(),
                'clock_in_time': record.clock_in_time.isoformat() if record.clock_in_time else None,
                'clock_out_time': record.clock_out_time.isoformat() if record.clock_out_time else None,
                'hours_worked': float(record.hours_worked) if record.hours_worked else 0.0,
                'approved': record.approved,
                'clock_in_location_valid': record.clock_in_location_valid,
                'clock_out_location_valid': record.clock_out_location_valid,
                'notes': record.notes
            })

        return jsonify({
            'success': True,
            'attendance': attendance_list,
            'total': len(attendance_list)
        })

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@api_bp.route('/admin/attendance/<int:attendance_id>/approve', methods=['POST'])
@token_required
def approve_attendance_record(current_user_id, attendance_id):
    """Approve or reject an attendance record (Admin only)"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin access required'}), 403

        # Get attendance record
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return jsonify({'message': 'Attendance record not found'}), 404

        # Get approval status from request
        data = request.get_json()
        approved = data.get('approved', True)

        # Update attendance record
        attendance.approved = approved
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Attendance record {"approved" if approved else "rejected"} successfully',
            'attendance': {
                'id': attendance.id,
                'approved': attendance.approved
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


@api_bp.route('/admin/attendance/stats', methods=['GET'])
@token_required
def get_attendance_stats(current_user_id):
    """Get attendance statistics (Admin only)"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'message': 'Unauthorized - Admin access required'}), 403

        # Get date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = Attendance.query

        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())

        all_records = query.all()

        # Calculate statistics
        total_records = len(all_records)
        approved_records = len([r for r in all_records if r.approved])
        pending_records = total_records - approved_records
        total_hours = sum([float(r.hours_worked) if r.hours_worked else 0 for r in all_records])

        # Get staff with most hours
        staff_hours = {}
        for record in all_records:
            if record.hours_worked:
                staff_hours[record.user_id] = staff_hours.get(record.user_id, 0) + float(record.hours_worked)

        top_staff = []
        for user_id, hours in sorted(staff_hours.items(), key=lambda x: x[1], reverse=True)[:5]:
            staff = User.query.get(user_id)
            if staff:
                top_staff.append({
                    'staff_name': staff.username,
                    'staff_role': staff.staff_role,
                    'total_hours': round(hours, 2)
                })

        return jsonify({
            'success': True,
            'stats': {
                'total_records': total_records,
                'approved_records': approved_records,
                'pending_records': pending_records,
                'total_hours': round(total_hours, 2),
                'average_hours_per_record': round(total_hours / total_records, 2) if total_records > 0 else 0,
                'top_staff': top_staff
            }
        })

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ==================== STAFF ATTENDANCE (CLOCK IN/OUT) ====================

@api_bp.route('/staff/attendance/clock-in', methods=['POST'])
@token_required
def staff_clock_in(current_user_id):
    """Staff clock in with ID verification and location tracking"""
    try:
        data = request.get_json()
        verify_id = data.get('verify_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Get current user
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'success': False, 'message': 'User not found or not a staff member'}), 404

        # Validate location data
        if not latitude or not longitude:
            return jsonify({'success': False, 'message': 'Location data is required for clock in'}), 400

        # Validate location (check if within hotel premises)
        # Hotel location (example coordinates - update with actual hotel location)
        HOTEL_LAT = 14.5995  # Example: Manila coordinates
        HOTEL_LON = 120.9842
        MAX_DISTANCE_KM = 0.5  # 500 meters radius
        
        location_valid = validate_location(float(latitude), float(longitude), HOTEL_LAT, HOTEL_LON, MAX_DISTANCE_KM)

        # Check if already clocked in today
        today = datetime.now().date()
        existing_attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).order_by(Attendance.id.desc()).first()

        if existing_attendance and existing_attendance.clock_in_time and not existing_attendance.clock_out_time:
            return jsonify({
                'success': False,
                'message': 'You are already clocked in. Please clock out first.'
            }), 400

        # Create new attendance record
        attendance = Attendance(
            user_id=current_user_id,
            date=today,
            clock_in_time=datetime.now(),
            clock_in_latitude=float(latitude),
            clock_in_longitude=float(longitude),
            clock_in_location_valid=location_valid,
            verified_by_id=verify_id or str(current_user_id),
            status='clocked_in',
            approved=False
        )
        db.session.add(attendance)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Clocked in successfully',
            'location_valid': location_valid,
            'attendance': {
                'id': attendance.id,
                'clock_in_time': attendance.clock_in_time.isoformat(),
                'date': attendance.date.isoformat(),
                'location_valid': location_valid
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

def validate_location(lat1, lon1, lat2, lon2, max_distance_km):
    """
    Calculate distance between two coordinates using Haversine formula
    Returns True if within max_distance_km
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Earth radius in kilometers
    R = 6371.0
    distance = R * c
    
    return distance <= max_distance_km


@api_bp.route('/staff/attendance/clock-out', methods=['POST'])
@token_required
def staff_clock_out(current_user_id):
    """Staff clock out with location tracking"""
    try:
        data = request.get_json()
        verify_id = data.get('verify_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Get current user
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'success': False, 'message': 'User not found or not a staff member'}), 404

        # Validate location data
        if not latitude or not longitude:
            return jsonify({'success': False, 'message': 'Location data is required for clock out'}), 400

        # Validate location
        HOTEL_LAT = 14.5995
        HOTEL_LON = 120.9842
        MAX_DISTANCE_KM = 0.5
        
        location_valid = validate_location(float(latitude), float(longitude), HOTEL_LAT, HOTEL_LON, MAX_DISTANCE_KM)

        # Find today's attendance record
        today = datetime.now().date()
        attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).order_by(Attendance.id.desc()).first()

        if not attendance:
            return jsonify({
                'success': False,
                'message': 'No clock-in record found for today. Please clock in first.'
            }), 400

        if attendance.clock_out_time:
            return jsonify({
                'success': False,
                'message': 'You have already clocked out for this shift.'
            }), 400

        # Update clock out time and location
        attendance.clock_out_time = datetime.now()
        attendance.clock_out_latitude = float(latitude)
        attendance.clock_out_longitude = float(longitude)
        attendance.clock_out_location_valid = location_valid
        attendance.status = 'clocked_out'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Clocked out successfully',
            'location_valid': location_valid,
            'attendance': {
                'id': attendance.id,
                'clock_in_time': attendance.clock_in_time.isoformat(),
                'clock_out_time': attendance.clock_out_time.isoformat(),
                'hours_worked': attendance.hours_worked,
                'date': attendance.date.isoformat(),
                'location_valid': location_valid
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@api_bp.route('/staff/attendance/status', methods=['GET'])
@token_required
def get_attendance_status(current_user_id):
    """Get current attendance status for staff"""
    try:
        today = datetime.now().date()
        attendance = Attendance.query.filter_by(
            user_id=current_user_id,
            date=today
        ).order_by(Attendance.id.desc()).first()

        if not attendance:
            return jsonify({
                'success': True,
                'is_clocked_in': False,
                'clock_in_time': None,
                'clock_out_time': None,
                'hours_worked': 0
            })

        return jsonify({
            'success': True,
            'is_clocked_in': attendance.clock_in_time is not None and attendance.clock_out_time is None,
            'clock_in_time': attendance.clock_in_time.isoformat() if attendance.clock_in_time else None,
            'clock_out_time': attendance.clock_out_time.isoformat() if attendance.clock_out_time else None,
            'hours_worked': attendance.hours_worked,
            'clock_in_location_valid': attendance.clock_in_location_valid,
            'clock_out_location_valid': attendance.clock_out_location_valid,
            'approved': attendance.approved
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/staff/attendance/history', methods=['GET'])
@token_required
def get_attendance_history(current_user_id):
    """Get attendance history for staff member"""
    try:
        from datetime import timedelta
        
        # Get date range from query params (default to last 30 days)
        days = int(request.args.get('days', 30))
        start_date = datetime.now().date() - timedelta(days=days)
        
        attendance_records = Attendance.query.filter(
            Attendance.user_id == current_user_id,
            Attendance.date >= start_date
        ).order_by(Attendance.date.desc()).all()
        
        result = []
        for record in attendance_records:
            result.append({
                'id': record.id,
                'date': record.date.isoformat(),
                'clock_in_time': record.clock_in_time.isoformat() if record.clock_in_time else None,
                'clock_out_time': record.clock_out_time.isoformat() if record.clock_out_time else None,
                'hours_worked': record.hours_worked,
                'status': record.status,
                'approved': record.approved,
                'clock_in_location_valid': record.clock_in_location_valid,
                'clock_out_location_valid': record.clock_out_location_valid,
                'notes': record.notes
            })
        
        return jsonify({
            'success': True,
            'attendance': result,
            'total_records': len(result)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ============================================
# AMENITIES MASTER API ENDPOINTS
# ============================================

@api_bp.route('/amenities', methods=['GET'])
def get_amenities():
    """Get all amenities from amenity_master table"""
    try:
        from models import AmenityMaster
        amenities = AmenityMaster.query.order_by(AmenityMaster.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'amenities': [{
                'id': a.id,
                'name': a.name,
                'icon_url': a.icon_url,
                'description': a.description,
                'created_at': a.created_at.isoformat() if a.created_at else None
            } for a in amenities]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenities', methods=['POST'])
@token_required
def create_amenity(current_user_id):
    """Create a new amenity"""
    try:
        from models import AmenityMaster
        
        data = request.get_json()
        
        # Validation
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Amenity name is required'}), 400
        
        if not data.get('icon_url'):
            return jsonify({'success': False, 'message': 'Icon URL is required'}), 400
        
        # Check if amenity name already exists
        existing = AmenityMaster.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Amenity with this name already exists'}), 400
        
        # Create new amenity
        amenity = AmenityMaster(
            name=data['name'],
            icon_url=data['icon_url'],
            description=data.get('description', '')
        )
        
        db.session.add(amenity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity created successfully',
            'amenity': {
                'id': amenity.id,
                'name': amenity.name,
                'icon_url': amenity.icon_url,
                'description': amenity.description,
                'created_at': amenity.created_at.isoformat() if amenity.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenities/<int:amenity_id>', methods=['PUT'])
@token_required
def update_amenity(current_user_id, amenity_id):
    """Update an existing amenity"""
    try:
        from models import AmenityMaster
        
        amenity = AmenityMaster.query.get(amenity_id)
        if not amenity:
            return jsonify({'success': False, 'message': 'Amenity not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Amenity name is required'}), 400
        
        if not data.get('icon_url'):
            return jsonify({'success': False, 'message': 'Icon URL is required'}), 400
        
        # Check if new name conflicts with another amenity
        if data['name'] != amenity.name:
            existing = AmenityMaster.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Amenity with this name already exists'}), 400
        
        # Update amenity
        amenity.name = data['name']
        amenity.icon_url = data['icon_url']
        amenity.description = data.get('description', '')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity updated successfully',
            'amenity': {
                'id': amenity.id,
                'name': amenity.name,
                'icon_url': amenity.icon_url,
                'description': amenity.description,
                'created_at': amenity.created_at.isoformat() if amenity.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenities/<int:amenity_id>', methods=['DELETE'])
@token_required
def delete_amenity(current_user_id, amenity_id):
    """Delete an amenity"""
    try:
        from models import AmenityMaster, AmenityDetail
        
        amenity = AmenityMaster.query.get(amenity_id)
        if not amenity:
            return jsonify({'success': False, 'message': 'Amenity not found'}), 404
        
        # Check if amenity is used in amenity details
        usage_count = AmenityDetail.query.filter_by(amenity_id=amenity_id).count()
        if usage_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete amenity. It is linked to {usage_count} room type(s). Remove the links first.'
            }), 400
        
        db.session.delete(amenity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# ROOM SIZE (ROOM TYPES) API ENDPOINTS
# ============================================

@api_bp.route('/room-sizes', methods=['GET'])
def get_room_sizes():
    """Get all room sizes/types"""
    try:
        from models import RoomSize
        room_sizes = RoomSize.query.order_by(RoomSize.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'room_sizes': [{
                'id': rs.id,
                'room_type_name': rs.room_type_name,
                'features': rs.features,
                'max_adults': rs.max_adults,
                'max_children': rs.max_children,
                'created_at': rs.created_at.isoformat() if rs.created_at else None
            } for rs in room_sizes]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/room-sizes', methods=['POST'])
@token_required
def create_room_size(current_user_id):
    """Create a new room size/type"""
    try:
        from models import RoomSize
        
        data = request.get_json()
        
        # Validation
        if not data.get('room_type_name'):
            return jsonify({'success': False, 'message': 'Room type name is required'}), 400
        
        if not data.get('max_adults') or int(data.get('max_adults', 0)) <= 0:
            return jsonify({'success': False, 'message': 'Max adults must be greater than 0'}), 400
        
        if data.get('max_children') is None or int(data.get('max_children', -1)) < 0:
            return jsonify({'success': False, 'message': 'Max children must be 0 or greater'}), 400
        
        # Check if room type name already exists
        existing = RoomSize.query.filter_by(room_type_name=data['room_type_name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Room type with this name already exists'}), 400
        
        # Create new room size
        room_size = RoomSize(
            room_type_name=data['room_type_name'],
            features=data.get('features', ''),
            max_adults=int(data['max_adults']),
            max_children=int(data['max_children'])
        )
        
        db.session.add(room_size)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room type created successfully',
            'room_size': {
                'id': room_size.id,
                'room_type_name': room_size.room_type_name,
                'features': room_size.features,
                'max_adults': room_size.max_adults,
                'max_children': room_size.max_children,
                'created_at': room_size.created_at.isoformat() if room_size.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/room-sizes/<int:room_size_id>', methods=['PUT'])
@token_required
def update_room_size(current_user_id, room_size_id):
    """Update an existing room size/type"""
    try:
        from models import RoomSize
        
        room_size = RoomSize.query.get(room_size_id)
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data.get('room_type_name'):
            return jsonify({'success': False, 'message': 'Room type name is required'}), 400
        
        if not data.get('max_adults') or int(data.get('max_adults', 0)) <= 0:
            return jsonify({'success': False, 'message': 'Max adults must be greater than 0'}), 400
        
        if data.get('max_children') is None or int(data.get('max_children', -1)) < 0:
            return jsonify({'success': False, 'message': 'Max children must be 0 or greater'}), 400
        
        # Check if new name conflicts with another room type
        if data['room_type_name'] != room_size.room_type_name:
            existing = RoomSize.query.filter_by(room_type_name=data['room_type_name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Room type with this name already exists'}), 400
        
        # Update room size
        room_size.room_type_name = data['room_type_name']
        room_size.features = data.get('features', '')
        room_size.max_adults = int(data['max_adults'])
        room_size.max_children = int(data['max_children'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room type updated successfully',
            'room_size': {
                'id': room_size.id,
                'room_type_name': room_size.room_type_name,
                'features': room_size.features,
                'max_adults': room_size.max_adults,
                'max_children': room_size.max_children,
                'created_at': room_size.created_at.isoformat() if room_size.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/room-sizes/<int:room_size_id>', methods=['DELETE'])
@token_required
def delete_room_size(current_user_id, room_size_id):
    """Delete a room size/type"""
    try:
        from models import RoomSize, Room, FloorPlan, AmenityDetail
        
        room_size = RoomSize.query.get(room_size_id)
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Check if room type is used in rooms
        rooms_count = Room.query.filter_by(room_size_id=room_size_id).count()
        if rooms_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete room type. It is used by {rooms_count} room(s). Delete or reassign the rooms first.'
            }), 400
        
        # Check if room type is used in floor plans
        floors_count = FloorPlan.query.filter_by(room_size_id=room_size_id).count()
        if floors_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete room type. It is used in {floors_count} floor plan(s). Delete or reassign the floor plans first.'
            }), 400
        
        # Check if room type is used in amenity details
        amenities_count = AmenityDetail.query.filter_by(room_size_id=room_size_id).count()
        if amenities_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete room type. It has {amenities_count} amenity link(s). Remove the amenity links first.'
            }), 400
        
        db.session.delete(room_size)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Room type deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# AMENITY DETAILS (AMENITY-ROOM TYPE MAPPING) API ENDPOINTS
# ============================================

@api_bp.route('/amenity-details', methods=['GET'])
def get_amenity_details():
    """Get all amenity-room type mappings"""
    try:
        from models import AmenityDetail, AmenityMaster, RoomSize
        
        details = AmenityDetail.query.all()
        
        return jsonify({
            'success': True,
            'amenity_details': [{
                'id': ad.id,
                'amenity_id': ad.amenity_id,
                'amenity_name': ad.amenity.name if ad.amenity else 'Unknown',
                'amenity_icon': ad.amenity.icon_url if ad.amenity else '',
                'room_size_id': ad.room_size_id,
                'room_type_name': ad.room_size.room_type_name if ad.room_size else 'Unknown',
                'created_at': ad.created_at.isoformat() if ad.created_at else None
            } for ad in details]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenity-details', methods=['POST'])
@token_required
def create_amenity_detail(current_user_id):
    """Create a new amenity-room type mapping"""
    try:
        from models import AmenityDetail, AmenityMaster, RoomSize
        
        data = request.get_json()
        
        # Validation
        if not data.get('amenity_id'):
            return jsonify({'success': False, 'message': 'Amenity is required'}), 400
        
        if not data.get('room_size_id'):
            return jsonify({'success': False, 'message': 'Room type is required'}), 400
        
        # Check if amenity exists
        amenity = AmenityMaster.query.get(data['amenity_id'])
        if not amenity:
            return jsonify({'success': False, 'message': 'Amenity not found'}), 404
        
        # Check if room size exists
        room_size = RoomSize.query.get(data['room_size_id'])
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Check if mapping already exists
        existing = AmenityDetail.query.filter_by(
            amenity_id=data['amenity_id'],
            room_size_id=data['room_size_id']
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': f'{amenity.name} is already linked to {room_size.room_type_name}'
            }), 400
        
        # Create new mapping
        detail = AmenityDetail(
            amenity_id=data['amenity_id'],
            room_size_id=data['room_size_id']
        )
        
        db.session.add(detail)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Amenity linked to room type successfully',
            'amenity_detail': {
                'id': detail.id,
                'amenity_id': detail.amenity_id,
                'amenity_name': detail.amenity.name,
                'amenity_icon': detail.amenity.icon_url,
                'room_size_id': detail.room_size_id,
                'room_type_name': detail.room_size.room_type_name,
                'created_at': detail.created_at.isoformat() if detail.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/amenity-details/<int:detail_id>', methods=['DELETE'])
@token_required
def delete_amenity_detail(current_user_id, detail_id):
    """Delete an amenity-room type mapping"""
    try:
        from models import AmenityDetail
        
        detail = AmenityDetail.query.get(detail_id)
        if not detail:
            return jsonify({'success': False, 'message': 'Mapping not found'}), 404
        
        amenity_name = detail.amenity.name if detail.amenity else 'Unknown'
        room_type_name = detail.room_size.room_type_name if detail.room_size else 'Unknown'
        
        db.session.delete(detail)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{amenity_name} unlinked from {room_type_name} successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# FLOOR PLANS API ENDPOINTS
# ============================================

@api_bp.route('/floor-plans', methods=['GET'])
def get_floor_plans():
    """Get all floor plans"""
    try:
        from models import FloorPlan, RoomSize
        
        floor_plans = FloorPlan.query.all()
        
        return jsonify({
            'success': True,
            'floor_plans': [{
                'id': fp.id,
                'floor_name': fp.floor_name,
                'room_size_id': fp.room_size_id,
                'room_type_name': fp.room_size.room_type_name if fp.room_size else 'Unknown',
                'number_of_rooms': fp.number_of_rooms,
                'start_room_number': fp.start_room_number,
                'generated_room_numbers': fp.generate_room_numbers(),
                'created_at': fp.created_at.isoformat() if fp.created_at else None
            } for fp in floor_plans]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/floor-plans', methods=['POST'])
@token_required
def create_floor_plan(current_user_id):
    """Create a new floor plan"""
    try:
        from models import FloorPlan, RoomSize
        
        data = request.get_json()
        
        # Validation
        if not data.get('floor_name'):
            return jsonify({'success': False, 'message': 'Floor name is required'}), 400
        
        if not data.get('room_size_id'):
            return jsonify({'success': False, 'message': 'Room type is required'}), 400
        
        if not data.get('number_of_rooms'):
            return jsonify({'success': False, 'message': 'Number of rooms is required'}), 400
        
        if not data.get('start_room_number'):
            return jsonify({'success': False, 'message': 'Start room number is required'}), 400
        
        # Check if room size exists
        room_size = RoomSize.query.get(data['room_size_id'])
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Check if floor name already exists
        existing = FloorPlan.query.filter_by(floor_name=data['floor_name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Floor with this name already exists'}), 400
        
        # Validate number of rooms
        try:
            number_of_rooms = int(data['number_of_rooms'])
            if number_of_rooms <= 0 or number_of_rooms > 100:
                return jsonify({'success': False, 'message': 'Number of rooms must be between 1 and 100'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid number of rooms'}), 400
        
        # Validate start room number
        try:
            int(data['start_room_number'])
        except ValueError:
            return jsonify({'success': False, 'message': 'Start room number must be numeric'}), 400
        
        # Create new floor plan
        floor_plan = FloorPlan(
            floor_name=data['floor_name'],
            room_size_id=data['room_size_id'],
            number_of_rooms=number_of_rooms,
            start_room_number=data['start_room_number']
        )
        
        db.session.add(floor_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Floor plan created successfully',
            'floor_plan': {
                'id': floor_plan.id,
                'floor_name': floor_plan.floor_name,
                'room_size_id': floor_plan.room_size_id,
                'room_type_name': floor_plan.room_size.room_type_name,
                'number_of_rooms': floor_plan.number_of_rooms,
                'start_room_number': floor_plan.start_room_number,
                'generated_room_numbers': floor_plan.generate_room_numbers(),
                'created_at': floor_plan.created_at.isoformat() if floor_plan.created_at else None
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/floor-plans/<int:floor_plan_id>', methods=['PUT'])
@token_required
def update_floor_plan(current_user_id, floor_plan_id):
    """Update an existing floor plan"""
    try:
        from models import FloorPlan, RoomSize, Room
        
        floor_plan = FloorPlan.query.get(floor_plan_id)
        if not floor_plan:
            return jsonify({'success': False, 'message': 'Floor plan not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data.get('floor_name'):
            return jsonify({'success': False, 'message': 'Floor name is required'}), 400
        
        if not data.get('room_size_id'):
            return jsonify({'success': False, 'message': 'Room type is required'}), 400
        
        if not data.get('number_of_rooms'):
            return jsonify({'success': False, 'message': 'Number of rooms is required'}), 400
        
        if not data.get('start_room_number'):
            return jsonify({'success': False, 'message': 'Start room number is required'}), 400
        
        # Check if new floor name conflicts with another floor
        if data['floor_name'] != floor_plan.floor_name:
            existing = FloorPlan.query.filter_by(floor_name=data['floor_name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Floor with this name already exists'}), 400
        
        # Check if room size exists
        room_size = RoomSize.query.get(data['room_size_id'])
        if not room_size:
            return jsonify({'success': False, 'message': 'Room type not found'}), 404
        
        # Validate number of rooms
        try:
            number_of_rooms = int(data['number_of_rooms'])
            if number_of_rooms <= 0 or number_of_rooms > 100:
                return jsonify({'success': False, 'message': 'Number of rooms must be between 1 and 100'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid number of rooms'}), 400
        
        # Validate start room number
        try:
            int(data['start_room_number'])
        except ValueError:
            return jsonify({'success': False, 'message': 'Start room number must be numeric'}), 400
        
        # Check if floor has rooms already created
        rooms_count = Room.query.filter_by(floor_id=floor_plan_id).count()
        if rooms_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot modify floor plan. It has {rooms_count} room(s) already created. Delete the rooms first.'
            }), 400
        
        # Update floor plan
        floor_plan.floor_name = data['floor_name']
        floor_plan.room_size_id = data['room_size_id']
        floor_plan.number_of_rooms = number_of_rooms
        floor_plan.start_room_number = data['start_room_number']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Floor plan updated successfully',
            'floor_plan': {
                'id': floor_plan.id,
                'floor_name': floor_plan.floor_name,
                'room_size_id': floor_plan.room_size_id,
                'room_type_name': floor_plan.room_size.room_type_name,
                'number_of_rooms': floor_plan.number_of_rooms,
                'start_room_number': floor_plan.start_room_number,
                'generated_room_numbers': floor_plan.generate_room_numbers(),
                'created_at': floor_plan.created_at.isoformat() if floor_plan.created_at else None
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/floor-plans/<int:floor_plan_id>', methods=['DELETE'])
@token_required
def delete_floor_plan(current_user_id, floor_plan_id):
    """Delete a floor plan"""
    try:
        from models import FloorPlan, Room
        
        floor_plan = FloorPlan.query.get(floor_plan_id)
        if not floor_plan:
            return jsonify({'success': False, 'message': 'Floor plan not found'}), 404
        
        # Check if floor has rooms
        rooms_count = Room.query.filter_by(floor_id=floor_plan_id).count()
        if rooms_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete floor plan. It has {rooms_count} room(s). Delete the rooms first.'
            }), 400
        
        floor_name = floor_plan.floor_name
        
        db.session.delete(floor_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Floor plan "{floor_name}" deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Review & Rating Routes
@api_bp.route('/reviews', methods=['POST'])
@token_required
def create_review(current_user_id):
    """Create a review for a completed booking"""
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        overall_rating = data.get('overall_rating')
        room_rating = data.get('room_rating')
        amenities_rating = data.get('amenities_rating')
        service_rating = data.get('service_rating')
        comment = data.get('comment', '')
        
        # Validate
        if not booking_id:
            return jsonify({'success': False, 'message': 'Booking ID is required'}), 400
        
        # If only overall_rating is provided, use it for all ratings
        if overall_rating and not (room_rating or amenities_rating or service_rating):
            room_rating = overall_rating
            amenities_rating = overall_rating
            service_rating = overall_rating
        
        # Validate all ratings are provided
        if not all([overall_rating, room_rating, amenities_rating, service_rating]):
            return jsonify({'success': False, 'message': 'All rating fields are required'}), 400
        
        # Validate rating values
        for rating_value in [overall_rating, room_rating, amenities_rating, service_rating]:
            if rating_value < 1 or rating_value > 5:
                return jsonify({'success': False, 'message': 'Ratings must be between 1 and 5'}), 400
        
        # Check if booking exists and belongs to user
        booking = Booking.query.get(booking_id)
        if not booking or booking.user_id != current_user_id:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Check if booking is completed (checked out)
        if booking.status not in ['checked_out', 'completed']:
            return jsonify({'success': False, 'message': 'Can only review completed stays'}), 400
        
        # Check if already reviewed
        existing_review = Rating.query.filter_by(booking_id=booking_id).first()
        if existing_review:
            return jsonify({'success': False, 'message': 'You have already reviewed this booking'}), 400
        
        # Create review
        review = Rating(
            user_id=current_user_id,
            booking_id=booking_id,
            overall_rating=overall_rating,
            room_rating=room_rating,
            amenities_rating=amenities_rating,
            service_rating=service_rating,
            comment=comment
        )
        db.session.add(review)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Review submitted successfully',
            'review': {
                'id': review.id,
                'overall_rating': review.overall_rating,
                'room_rating': review.room_rating,
                'amenities_rating': review.amenities_rating,
                'service_rating': review.service_rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/reviews', methods=['GET'])
def get_reviews():
    """Get all reviews (for admin)"""
    try:
        reviews = Rating.query.order_by(Rating.created_at.desc()).all()
        reviews_data = []
        
        for review in reviews:
            user = User.query.get(review.user_id)
            booking = Booking.query.get(review.booking_id)
            room = Room.query.get(booking.room_id) if booking else None
            
            reviews_data.append({
                'id': review.id,
                'user_id': review.user_id,
                'user_name': user.username if user else 'Unknown',
                'room_id': booking.room_id if booking else None,
                'room_number': room.room_number if room else 'N/A',
                'booking_id': review.booking_id,
                'rating': review.overall_rating,  # Use overall_rating field
                'overall_rating': review.overall_rating,
                'room_rating': review.room_rating,
                'amenities_rating': review.amenities_rating,
                'service_rating': review.service_rating,
                'comment': review.comment or '',
                'admin_reply': review.admin_reply or '',
                'created_at': review.created_at.isoformat(),
                'replied_at': None  # Rating model doesn't have replied_at field
            })
        
        return jsonify({'success': True, 'reviews': reviews_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/reviews/<int:review_id>/reply', methods=['POST'])
@token_required
def reply_to_review(current_user_id, review_id):
    """Admin reply to a review"""
    try:
        # Check if user is admin
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        reply = data.get('reply', '')
        
        if not reply:
            return jsonify({'success': False, 'message': 'Reply cannot be empty'}), 400
        
        # Get review
        review = Rating.query.get(review_id)
        if not review:
            return jsonify({'success': False, 'message': 'Review not found'}), 404
        
        # Update review with admin reply
        review.admin_reply = reply
        
        # Create notification for the user
        notification = Notification(
            user_id=review.user_id,
            title='Admin replied to your review',
            message=f'The hotel has responded to your review: "{reply[:100]}..."'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reply sent successfully',
            'review': {
                'id': review.id,
                'admin_reply': review.admin_reply
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/my-reviews', methods=['GET'])
@token_required
def get_my_reviews(current_user_id):
    """Get current user's reviews with admin replies"""
    try:
        reviews = Rating.query.filter_by(user_id=current_user_id).order_by(Rating.created_at.desc()).all()
        reviews_data = []
        
        for review in reviews:
            room = Room.query.get(review.room_id)
            booking = Booking.query.get(review.booking_id)
            
            reviews_data.append({
                'id': review.id,
                'room_id': review.room_id,
                'room_number': room.room_number if room else 'N/A',
                'booking_id': review.booking_id,
                'rating': review.rating,
                'comment': review.comment or '',
                'admin_reply': review.admin_reply or '',
                'created_at': review.created_at.isoformat(),
                'replied_at': review.replied_at.isoformat() if review.replied_at else None,
                'has_reply': review.admin_reply is not None
            })
        
        return jsonify({'success': True, 'reviews': reviews_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# INVENTORY MANAGEMENT API ENDPOINTS
# ============================================

# Inventory Item Management
@api_bp.route('/admin/inventory/items', methods=['POST'])
@token_required
def create_inventory_item(current_user_id):
    """Create a new inventory item"""
    from models import InventoryItem, InventoryCategory, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'category_id', 'unit_of_measure', 'reorder_point']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Validate category exists
        category = InventoryCategory.query.get(data['category_id'])
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        # Validate supplier if provided
        if data.get('preferred_supplier_id'):
            supplier = Supplier.query.get(data['preferred_supplier_id'])
            if not supplier:
                return jsonify({'success': False, 'message': 'Supplier not found'}), 404
        
        # Check for duplicate name in category
        existing = InventoryItem.query.filter_by(
            name=data['name'],
            category_id=data['category_id']
        ).first()
        if existing:
            return jsonify({'success': False, 'message': 'Item name already exists in this category'}), 409
        
        # Create item
        item = InventoryItem(
            name=data['name'],
            category_id=data['category_id'],
            unit_of_measure=data['unit_of_measure'],
            current_stock=data.get('current_stock', 0.0),
            reorder_point=data['reorder_point'],
            preferred_supplier_id=data.get('preferred_supplier_id'),
            unit_cost=data.get('unit_cost'),
            status='active'
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory item created successfully',
            'item': {
                'id': item.id,
                'name': item.name,
                'category_id': item.category_id,
                'category_name': category.name,
                'unit_of_measure': item.unit_of_measure,
                'current_stock': item.current_stock,
                'reorder_point': item.reorder_point,
                'stock_status': item.stock_status,
                'status': item.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/items', methods=['GET'])
@token_required
def get_inventory_items(current_user_id):
    """Get all inventory items"""
    from models import InventoryItem, InventoryCategory, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get query parameters for filtering
        category_id = request.args.get('category_id', type=int)
        status = request.args.get('status', 'active')
        low_stock_only = request.args.get('low_stock', 'false').lower() == 'true'
        
        # Build query
        query = InventoryItem.query
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if status:
            query = query.filter_by(status=status)
        
        items = query.all()
        
        # Filter for low stock if requested
        if low_stock_only:
            items = [item for item in items if item.is_low_stock]
        
        items_data = []
        for item in items:
            category = InventoryCategory.query.get(item.category_id)
            supplier = Supplier.query.get(item.preferred_supplier_id) if item.preferred_supplier_id else None
            
            items_data.append({
                'id': item.id,
                'name': item.name,
                'category_id': item.category_id,
                'category_name': category.name if category else 'N/A',
                'unit_of_measure': item.unit_of_measure,
                'current_stock': item.current_stock,
                'reorder_point': item.reorder_point,
                'unit_cost': item.unit_cost,
                'preferred_supplier_id': item.preferred_supplier_id,
                'supplier_name': supplier.name if supplier else None,
                'last_restocked_date': item.last_restocked_date.isoformat() if item.last_restocked_date else None,
                'stock_status': item.stock_status,
                'is_low_stock': item.is_low_stock,
                'status': item.status,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat()
            })
        
        return jsonify({'success': True, 'items': items_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/items/<int:item_id>', methods=['GET'])
@token_required
def get_inventory_item(current_user_id, item_id):
    """Get a specific inventory item"""
    from models import InventoryItem, InventoryCategory, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        item = InventoryItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        category = InventoryCategory.query.get(item.category_id)
        supplier = Supplier.query.get(item.preferred_supplier_id) if item.preferred_supplier_id else None
        
        return jsonify({
            'success': True,
            'item': {
                'id': item.id,
                'name': item.name,
                'category_id': item.category_id,
                'category_name': category.name if category else 'N/A',
                'unit_of_measure': item.unit_of_measure,
                'current_stock': item.current_stock,
                'reorder_point': item.reorder_point,
                'unit_cost': item.unit_cost,
                'preferred_supplier_id': item.preferred_supplier_id,
                'supplier_name': supplier.name if supplier else None,
                'last_restocked_date': item.last_restocked_date.isoformat() if item.last_restocked_date else None,
                'stock_status': item.stock_status,
                'is_low_stock': item.is_low_stock,
                'status': item.status,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/items/<int:item_id>', methods=['PUT'])
@token_required
def update_inventory_item(current_user_id, item_id):
    """Update an inventory item"""
    from models import InventoryItem, InventoryCategory, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        item = InventoryItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        data = request.get_json()
        
        # Validate category if being updated
        if 'category_id' in data:
            category = InventoryCategory.query.get(data['category_id'])
            if not category:
                return jsonify({'success': False, 'message': 'Category not found'}), 404
            item.category_id = data['category_id']
        
        # Validate supplier if being updated
        if 'preferred_supplier_id' in data and data['preferred_supplier_id']:
            supplier = Supplier.query.get(data['preferred_supplier_id'])
            if not supplier:
                return jsonify({'success': False, 'message': 'Supplier not found'}), 404
            item.preferred_supplier_id = data['preferred_supplier_id']
        
        # Check for duplicate name if name is being changed
        if 'name' in data and data['name'] != item.name:
            existing = InventoryItem.query.filter_by(
                name=data['name'],
                category_id=item.category_id
            ).filter(InventoryItem.id != item_id).first()
            if existing:
                return jsonify({'success': False, 'message': 'Item name already exists in this category'}), 409
            item.name = data['name']
        
        # Update other fields
        if 'unit_of_measure' in data:
            item.unit_of_measure = data['unit_of_measure']
        if 'reorder_point' in data:
            item.reorder_point = data['reorder_point']
        if 'unit_cost' in data:
            item.unit_cost = data['unit_cost']
        if 'status' in data:
            item.status = data['status']
        
        db.session.commit()
        
        category = InventoryCategory.query.get(item.category_id)
        
        return jsonify({
            'success': True,
            'message': 'Inventory item updated successfully',
            'item': {
                'id': item.id,
                'name': item.name,
                'category_id': item.category_id,
                'category_name': category.name if category else 'N/A',
                'unit_of_measure': item.unit_of_measure,
                'current_stock': item.current_stock,
                'reorder_point': item.reorder_point,
                'stock_status': item.stock_status,
                'status': item.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/items/<int:item_id>', methods=['DELETE'])
@token_required
def delete_inventory_item(current_user_id, item_id):
    """Archive an inventory item (soft delete)"""
    from models import InventoryItem
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        item = InventoryItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        # Soft delete - just mark as archived
        item.status = 'archived'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory item archived successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Stock Transaction Endpoints
@api_bp.route('/admin/inventory/receipt', methods=['POST'])
@token_required
def record_stock_receipt(current_user_id):
    """Record stock receipt from supplier"""
    from models import InventoryItem, InventoryTransaction, Supplier, LowStockAlert
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_id', 'quantity', 'unit_cost']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Validate quantity is positive
        if data['quantity'] <= 0:
            return jsonify({'success': False, 'message': 'Quantity must be a positive number'}), 400
        
        # Get item
        item = InventoryItem.query.get(data['item_id'])
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        # Validate supplier if provided
        supplier_id = data.get('supplier_id')
        if supplier_id:
            supplier = Supplier.query.get(supplier_id)
            if not supplier:
                return jsonify({'success': False, 'message': 'Supplier not found'}), 404
        
        # Calculate total cost
        quantity = float(data['quantity'])
        unit_cost = float(data['unit_cost'])
        total_cost = quantity * unit_cost
        
        # Update stock
        item.current_stock += quantity
        item.last_restocked_date = datetime.utcnow()
        if unit_cost:
            item.unit_cost = unit_cost
        
        # Create transaction record
        transaction = InventoryTransaction(
            item_id=item.id,
            transaction_type='receipt',
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            supplier_id=supplier_id,
            user_id=current_user_id,
            notes=data.get('notes'),
            transaction_date=datetime.utcnow()
        )
        
        db.session.add(transaction)
        
        # Clear low stock alert if stock is now above reorder point
        if item.current_stock >= item.reorder_point:
            unacknowledged_alerts = LowStockAlert.query.filter_by(
                item_id=item.id,
                acknowledged=False
            ).all()
            for alert in unacknowledged_alerts:
                alert.acknowledged = True
                alert.acknowledged_by = current_user_id
                alert.acknowledged_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Stock receipt recorded successfully',
            'transaction': {
                'id': transaction.id,
                'item_id': item.id,
                'item_name': item.name,
                'quantity': quantity,
                'unit_cost': unit_cost,
                'total_cost': total_cost,
                'new_stock_level': item.current_stock,
                'transaction_date': transaction.transaction_date.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/staff/inventory/usage', methods=['POST'])
@token_required
def record_inventory_usage(current_user_id):
    """Record inventory usage by staff"""
    from models import InventoryItem, InventoryTransaction, Department, LowStockAlert
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_id', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Validate quantity is positive
        if data['quantity'] <= 0:
            return jsonify({'success': False, 'message': 'Quantity must be a positive number'}), 400
        
        # Get item
        item = InventoryItem.query.get(data['item_id'])
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        quantity = float(data['quantity'])
        
        # Check if sufficient stock available
        if item.current_stock < quantity:
            return jsonify({
                'success': False,
                'message': f'Insufficient stock available. Current stock: {item.current_stock}, Requested: {quantity}'
            }), 400
        
        # Get department (from data or user's department)
        department_id = data.get('department_id')
        if not department_id and user.staff_role:
            # Try to find department by staff role
            dept = Department.query.filter_by(name=user.staff_role).first()
            if dept:
                department_id = dept.id
        
        # Update stock
        item.current_stock -= quantity
        
        # Create transaction record
        transaction = InventoryTransaction(
            item_id=item.id,
            transaction_type='usage',
            quantity=quantity,
            department_id=department_id,
            user_id=current_user_id,
            notes=data.get('notes'),
            transaction_date=datetime.utcnow()
        )
        
        db.session.add(transaction)
        
        # Check if low stock alert needed
        if item.current_stock < item.reorder_point:
            # Check if alert already exists
            existing_alert = LowStockAlert.query.filter_by(
                item_id=item.id,
                acknowledged=False
            ).first()
            
            if not existing_alert:
                alert = LowStockAlert(
                    item_id=item.id,
                    current_stock=item.current_stock,
                    reorder_point=item.reorder_point,
                    alert_date=datetime.utcnow()
                )
                db.session.add(alert)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory usage recorded successfully',
            'transaction': {
                'id': transaction.id,
                'item_id': item.id,
                'item_name': item.name,
                'quantity': quantity,
                'new_stock_level': item.current_stock,
                'is_low_stock': item.is_low_stock,
                'transaction_date': transaction.transaction_date.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/transfer', methods=['POST'])
@token_required
def transfer_inventory(current_user_id):
    """Transfer inventory between departments"""
    from models import InventoryItem, InventoryTransaction, Department
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_id', 'quantity', 'source_department_id', 'destination_department_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Validate quantity is positive
        if data['quantity'] <= 0:
            return jsonify({'success': False, 'message': 'Quantity must be a positive number'}), 400
        
        # Validate source and destination are different
        if data['source_department_id'] == data['destination_department_id']:
            return jsonify({'success': False, 'message': 'Source and destination departments must be different'}), 400
        
        # Get item
        item = InventoryItem.query.get(data['item_id'])
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        # Validate departments exist
        source_dept = Department.query.get(data['source_department_id'])
        dest_dept = Department.query.get(data['destination_department_id'])
        if not source_dept or not dest_dept:
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        quantity = float(data['quantity'])
        
        # Check if sufficient stock available
        if item.current_stock < quantity:
            return jsonify({
                'success': False,
                'message': f'Insufficient stock available. Current stock: {item.current_stock}, Requested: {quantity}'
            }), 400
        
        # Create transaction records for both departments
        # Source department (outgoing)
        source_transaction = InventoryTransaction(
            item_id=item.id,
            transaction_type='transfer',
            quantity=-quantity,  # Negative for outgoing
            source_department_id=data['source_department_id'],
            destination_department_id=data['destination_department_id'],
            user_id=current_user_id,
            notes=data.get('notes'),
            transaction_date=datetime.utcnow()
        )
        
        # Destination department (incoming)
        dest_transaction = InventoryTransaction(
            item_id=item.id,
            transaction_type='transfer',
            quantity=quantity,  # Positive for incoming
            source_department_id=data['source_department_id'],
            destination_department_id=data['destination_department_id'],
            user_id=current_user_id,
            notes=data.get('notes'),
            transaction_date=datetime.utcnow()
        )
        
        db.session.add(source_transaction)
        db.session.add(dest_transaction)
        
        # Note: Total stock remains unchanged in transfers
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory transfer recorded successfully',
            'transfer': {
                'item_id': item.id,
                'item_name': item.name,
                'quantity': quantity,
                'from_department': source_dept.name,
                'to_department': dest_dept.name,
                'total_stock': item.current_stock,
                'transaction_date': source_transaction.transaction_date.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/adjustment', methods=['POST'])
@token_required
def adjust_inventory(current_user_id):
    """Perform stock adjustment (audit)"""
    from models import InventoryItem, InventoryTransaction, LowStockAlert
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['item_id', 'new_quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Get item
        item = InventoryItem.query.get(data['item_id'])
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        
        old_quantity = item.current_stock
        new_quantity = float(data['new_quantity'])
        variance = new_quantity - old_quantity
        
        # Check if reason is required for large adjustments (threshold: 10% or more)
        threshold = item.reorder_point * 0.1  # 10% of reorder point
        if abs(variance) > threshold and not data.get('adjustment_reason'):
            return jsonify({
                'success': False,
                'message': 'Adjustment reason required for variance exceeding threshold'
            }), 400
        
        # Update stock
        item.current_stock = new_quantity
        
        # Create transaction record
        transaction = InventoryTransaction(
            item_id=item.id,
            transaction_type='adjustment',
            quantity=variance,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            adjustment_reason=data.get('adjustment_reason'),
            user_id=current_user_id,
            notes=data.get('notes'),
            transaction_date=datetime.utcnow()
        )
        
        db.session.add(transaction)
        
        # Check if low stock alert needed
        if item.current_stock < item.reorder_point:
            existing_alert = LowStockAlert.query.filter_by(
                item_id=item.id,
                acknowledged=False
            ).first()
            
            if not existing_alert:
                alert = LowStockAlert(
                    item_id=item.id,
                    current_stock=item.current_stock,
                    reorder_point=item.reorder_point,
                    alert_date=datetime.utcnow()
                )
                db.session.add(alert)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Stock adjustment recorded successfully',
            'adjustment': {
                'id': transaction.id,
                'item_id': item.id,
                'item_name': item.name,
                'old_quantity': old_quantity,
                'new_quantity': new_quantity,
                'variance': variance,
                'adjustment_reason': data.get('adjustment_reason'),
                'transaction_date': transaction.transaction_date.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Low Stock Alert Endpoints
@api_bp.route('/admin/inventory/alerts', methods=['GET'])
@token_required
def get_low_stock_alerts(current_user_id):
    """Get all low stock alerts"""
    from models import LowStockAlert, InventoryItem, InventoryCategory, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get query parameters
        acknowledged = request.args.get('acknowledged', 'false').lower()
        
        # Build query
        query = LowStockAlert.query
        
        if acknowledged == 'false':
            query = query.filter_by(acknowledged=False)
        elif acknowledged == 'true':
            query = query.filter_by(acknowledged=True)
        # If 'all', don't filter by acknowledged status
        
        alerts = query.order_by(LowStockAlert.alert_date.desc()).all()
        
        alerts_data = []
        for alert in alerts:
            item = InventoryItem.query.get(alert.item_id)
            if not item:
                continue
            
            category = InventoryCategory.query.get(item.category_id)
            supplier = Supplier.query.get(item.preferred_supplier_id) if item.preferred_supplier_id else None
            acknowledger = User.query.get(alert.acknowledged_by) if alert.acknowledged_by else None
            
            alerts_data.append({
                'id': alert.id,
                'item_id': item.id,
                'item_name': item.name,
                'category_name': category.name if category else 'N/A',
                'unit_of_measure': item.unit_of_measure,
                'current_stock': alert.current_stock,
                'reorder_point': alert.reorder_point,
                'shortage': alert.reorder_point - alert.current_stock,
                'preferred_supplier_id': item.preferred_supplier_id,
                'supplier_name': supplier.name if supplier else None,
                'supplier_contact': supplier.phone if supplier else None,
                'supplier_email': supplier.email if supplier else None,
                'alert_date': alert.alert_date.isoformat(),
                'acknowledged': alert.acknowledged,
                'acknowledged_by': acknowledger.username if acknowledger else None,
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts_data,
            'total_count': len(alerts_data),
            'unacknowledged_count': len([a for a in alerts_data if not a['acknowledged']])
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@token_required
def acknowledge_alert(current_user_id, alert_id):
    """Acknowledge a low stock alert"""
    from models import LowStockAlert, InventoryItem
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        alert = LowStockAlert.query.get(alert_id)
        if not alert:
            return jsonify({'success': False, 'message': 'Alert not found'}), 404
        
        if alert.acknowledged:
            return jsonify({'success': False, 'message': 'Alert already acknowledged'}), 400
        
        # Acknowledge the alert
        alert.acknowledged = True
        alert.acknowledged_by = current_user_id
        alert.acknowledged_at = datetime.utcnow()
        
        db.session.commit()
        
        item = InventoryItem.query.get(alert.item_id)
        
        return jsonify({
            'success': True,
            'message': 'Alert acknowledged successfully',
            'alert': {
                'id': alert.id,
                'item_id': item.id if item else None,
                'item_name': item.name if item else 'N/A',
                'acknowledged': True,
                'acknowledged_by': user.username,
                'acknowledged_at': alert.acknowledged_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/alerts/acknowledge-all', methods=['POST'])
@token_required
def acknowledge_all_alerts(current_user_id):
    """Acknowledge all unacknowledged low stock alerts"""
    from models import LowStockAlert
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get all unacknowledged alerts
        alerts = LowStockAlert.query.filter_by(acknowledged=False).all()
        
        count = 0
        for alert in alerts:
            alert.acknowledged = True
            alert.acknowledged_by = current_user_id
            alert.acknowledged_at = datetime.utcnow()
            count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{count} alert(s) acknowledged successfully',
            'count': count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# CATEGORY MANAGEMENT ENDPOINTS
# ============================================================================

@api_bp.route('/admin/inventory/categories', methods=['POST'])
@token_required
def create_category(current_user_id):
    """Create a new inventory category"""
    from models import InventoryCategory
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({'success': False, 'message': 'Category name is required'}), 400
        
        # Check for duplicate name
        existing = InventoryCategory.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Category name already exists'}), 409
        
        # Create category
        category = InventoryCategory(
            name=data['name'],
            description=data.get('description')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'created_at': category.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/categories', methods=['GET'])
@token_required
def get_categories(current_user_id):
    """Get all inventory categories"""
    from models import InventoryCategory, InventoryItem
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        categories = InventoryCategory.query.order_by(InventoryCategory.name).all()
        
        categories_data = []
        for category in categories:
            # Count items in this category
            item_count = InventoryItem.query.filter_by(category_id=category.id, status='active').count()
            
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'item_count': item_count,
                'created_at': category.created_at.isoformat(),
                'updated_at': category.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'categories': categories_data,
            'total_count': len(categories_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/categories/<int:category_id>', methods=['PUT'])
@token_required
def update_category(current_user_id, category_id):
    """Update an inventory category"""
    from models import InventoryCategory
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        category = InventoryCategory.query.get(category_id)
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        data = request.get_json()
        
        # Check for duplicate name if name is being changed
        if 'name' in data and data['name'] != category.name:
            existing = InventoryCategory.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Category name already exists'}), 409
            category.name = data['name']
        
        # Update description if provided
        if 'description' in data:
            category.description = data['description']
        
        category.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category updated successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'updated_at': category.updated_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/categories/<int:category_id>', methods=['DELETE'])
@token_required
def delete_category(current_user_id, category_id):
    """Delete an inventory category"""
    from models import InventoryCategory, InventoryItem
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        category = InventoryCategory.query.get(category_id)
        if not category:
            return jsonify({'success': False, 'message': 'Category not found'}), 404
        
        # Check if category has items
        items_count = InventoryItem.query.filter_by(category_id=category_id).count()
        if items_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete category with {items_count} assigned item(s). Please reassign or delete items first.'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# SUPPLIER MANAGEMENT ENDPOINTS
# ============================================================================

@api_bp.route('/admin/inventory/suppliers', methods=['POST'])
@token_required
def create_supplier(current_user_id):
    """Create a new supplier"""
    from models import Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'name' not in data:
            return jsonify({'success': False, 'message': 'Supplier name is required'}), 400
        
        # Check for duplicate name
        existing = Supplier.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Supplier name already exists'}), 409
        
        # Create supplier
        supplier = Supplier(
            name=data['name'],
            contact_person=data.get('contact_person'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            payment_terms=data.get('payment_terms')
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Supplier created successfully',
            'supplier': {
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'email': supplier.email,
                'phone': supplier.phone,
                'address': supplier.address,
                'payment_terms': supplier.payment_terms,
                'created_at': supplier.created_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/suppliers', methods=['GET'])
@token_required
def get_suppliers(current_user_id):
    """Get all suppliers"""
    from models import Supplier, InventoryItem, InventoryTransaction
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        suppliers_data = []
        for supplier in suppliers:
            # Count items using this supplier
            item_count = InventoryItem.query.filter_by(preferred_supplier_id=supplier.id, status='active').count()
            
            # Count transactions with this supplier
            transaction_count = InventoryTransaction.query.filter_by(supplier_id=supplier.id).count()
            
            suppliers_data.append({
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'email': supplier.email,
                'phone': supplier.phone,
                'address': supplier.address,
                'payment_terms': supplier.payment_terms,
                'item_count': item_count,
                'transaction_count': transaction_count,
                'created_at': supplier.created_at.isoformat(),
                'updated_at': supplier.updated_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'suppliers': suppliers_data,
            'total_count': len(suppliers_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/suppliers/<int:supplier_id>', methods=['PUT'])
@token_required
def update_supplier(current_user_id, supplier_id):
    """Update a supplier"""
    from models import Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier not found'}), 404
        
        data = request.get_json()
        
        # Check for duplicate name if name is being changed
        if 'name' in data and data['name'] != supplier.name:
            existing = Supplier.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({'success': False, 'message': 'Supplier name already exists'}), 409
            supplier.name = data['name']
        
        # Update other fields if provided
        if 'contact_person' in data:
            supplier.contact_person = data['contact_person']
        if 'email' in data:
            supplier.email = data['email']
        if 'phone' in data:
            supplier.phone = data['phone']
        if 'address' in data:
            supplier.address = data['address']
        if 'payment_terms' in data:
            supplier.payment_terms = data['payment_terms']
        
        supplier.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Supplier updated successfully',
            'supplier': {
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'email': supplier.email,
                'phone': supplier.phone,
                'address': supplier.address,
                'payment_terms': supplier.payment_terms,
                'updated_at': supplier.updated_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/suppliers/<int:supplier_id>', methods=['DELETE'])
@token_required
def delete_supplier(current_user_id, supplier_id):
    """Delete a supplier"""
    from models import Supplier, InventoryItem, InventoryTransaction
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return jsonify({'success': False, 'message': 'Supplier not found'}), 404
        
        # Check if supplier has items or transactions
        items_count = InventoryItem.query.filter_by(preferred_supplier_id=supplier_id).count()
        transactions_count = InventoryTransaction.query.filter_by(supplier_id=supplier_id).count()
        
        if items_count > 0 or transactions_count > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete supplier with {items_count} assigned item(s) and {transactions_count} transaction(s). Please reassign items and preserve transaction history.'
            }), 400
        
        db.session.delete(supplier)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Supplier deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# REPORTING ENDPOINTS
# ============================================================================

@api_bp.route('/admin/inventory/reports/summary', methods=['GET'])
@token_required
def get_inventory_summary_report(current_user_id):
    """Get inventory summary report"""
    from models import InventoryItem, InventoryCategory, Supplier, InventoryTransaction
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get total counts
        total_items = InventoryItem.query.filter_by(status='active').count()
        total_categories = InventoryCategory.query.count()
        total_suppliers = Supplier.query.count()
        
        # Get total inventory value
        items = InventoryItem.query.filter_by(status='active').all()
        total_value = sum(item.quantity * item.unit_cost for item in items if item.quantity and item.unit_cost)
        
        # Get low stock count
        low_stock_count = InventoryItem.query.filter(
            InventoryItem.status == 'active',
            InventoryItem.quantity <= InventoryItem.min_quantity
        ).count()
        
        # Get items by category
        categories_data = []
        categories = InventoryCategory.query.all()
        for category in categories:
            category_items = InventoryItem.query.filter_by(category_id=category.id, status='active').all()
            category_value = sum(item.quantity * item.unit_cost for item in category_items if item.quantity and item.unit_cost)
            
            categories_data.append({
                'category_id': category.id,
                'category_name': category.name,
                'item_count': len(category_items),
                'total_value': float(category_value)
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_items': total_items,
                'total_categories': total_categories,
                'total_suppliers': total_suppliers,
                'total_inventory_value': float(total_value),
                'low_stock_items': low_stock_count,
                'categories': categories_data
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/reports/low-stock', methods=['GET'])
@token_required
def get_low_stock_report(current_user_id):
    """Get low stock items report"""
    from models import InventoryItem, InventoryCategory, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get filter parameters
        category_id = request.args.get('category_id', type=int)
        
        # Build query
        query = InventoryItem.query.filter(
            InventoryItem.status == 'active',
            InventoryItem.quantity <= InventoryItem.min_quantity
        )
        
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        items = query.order_by(InventoryItem.quantity.asc()).all()
        
        items_data = []
        for item in items:
            category = InventoryCategory.query.get(item.category_id) if item.category_id else None
            supplier = Supplier.query.get(item.preferred_supplier_id) if item.preferred_supplier_id else None
            
            shortage = item.min_quantity - item.quantity if item.quantity else item.min_quantity
            
            items_data.append({
                'id': item.id,
                'name': item.name,
                'sku': item.sku,
                'category': category.name if category else None,
                'current_quantity': item.quantity or 0,
                'min_quantity': item.min_quantity or 0,
                'shortage': shortage,
                'unit': item.unit,
                'preferred_supplier': supplier.name if supplier else None,
                'supplier_contact': supplier.phone if supplier else None,
                'unit_cost': float(item.unit_cost) if item.unit_cost else 0.0,
                'reorder_cost': float(shortage * item.unit_cost) if item.unit_cost else 0.0
            })
        
        return jsonify({
            'success': True,
            'items': items_data,
            'total_count': len(items_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/reports/usage', methods=['GET'])
@token_required
def get_usage_report(current_user_id):
    """Get inventory usage report"""
    from models import InventoryTransaction, InventoryTransactionItem, InventoryItem, InventoryCategory
    from sqlalchemy import func
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category_id = request.args.get('category_id', type=int)
        
        # Build query for usage transactions
        query = db.session.query(
            InventoryTransactionItem.item_id,
            func.sum(InventoryTransactionItem.quantity).label('total_used')
        ).join(
            InventoryTransaction,
            InventoryTransaction.id == InventoryTransactionItem.transaction_id
        ).filter(
            InventoryTransaction.transaction_type == 'usage'
        )
        
        # Apply date filters
        if start_date:
            query = query.filter(InventoryTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(InventoryTransaction.transaction_date <= end_date)
        
        # Group by item
        query = query.group_by(InventoryTransactionItem.item_id)
        
        results = query.all()
        
        usage_data = []
        for item_id, total_used in results:
            item = InventoryItem.query.get(item_id)
            if not item:
                continue
            
            # Apply category filter
            if category_id and item.category_id != category_id:
                continue
            
            category = InventoryCategory.query.get(item.category_id) if item.category_id else None
            
            usage_data.append({
                'item_id': item.id,
                'item_name': item.name,
                'sku': item.sku,
                'category': category.name if category else None,
                'total_used': int(total_used),
                'unit': item.unit,
                'current_quantity': item.quantity or 0,
                'unit_cost': float(item.unit_cost) if item.unit_cost else 0.0,
                'total_cost': float(total_used * item.unit_cost) if item.unit_cost else 0.0
            })
        
        # Sort by total used (descending)
        usage_data.sort(key=lambda x: x['total_used'], reverse=True)
        
        return jsonify({
            'success': True,
            'usage': usage_data,
            'total_count': len(usage_data),
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/reports/transactions', methods=['GET'])
@token_required
def get_transactions_report(current_user_id):
    """Get inventory transactions report"""
    from models import InventoryTransaction, InventoryTransactionItem, InventoryItem, Supplier
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        transaction_type = request.args.get('transaction_type')
        item_id = request.args.get('item_id', type=int)
        
        # Build query
        query = InventoryTransaction.query
        
        # Apply filters
        if start_date:
            query = query.filter(InventoryTransaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(InventoryTransaction.transaction_date <= end_date)
        if transaction_type:
            query = query.filter(InventoryTransaction.transaction_type == transaction_type)
        
        transactions = query.order_by(InventoryTransaction.transaction_date.desc()).all()
        
        transactions_data = []
        for transaction in transactions:
            # Get transaction items
            items = InventoryTransactionItem.query.filter_by(transaction_id=transaction.id).all()
            
            # Apply item filter if specified
            if item_id:
                items = [item for item in items if item.item_id == item_id]
                if not items:
                    continue
            
            items_data = []
            for trans_item in items:
                item = InventoryItem.query.get(trans_item.item_id)
                if item:
                    items_data.append({
                        'item_id': item.id,
                        'item_name': item.name,
                        'sku': item.sku,
                        'quantity': trans_item.quantity,
                        'unit_cost': float(trans_item.unit_cost) if trans_item.unit_cost else 0.0,
                        'total_cost': float(trans_item.quantity * trans_item.unit_cost) if trans_item.unit_cost else 0.0
                    })
            
            supplier = Supplier.query.get(transaction.supplier_id) if transaction.supplier_id else None
            performed_by = User.query.get(transaction.performed_by) if transaction.performed_by else None
            
            transactions_data.append({
                'id': transaction.id,
                'transaction_type': transaction.transaction_type,
                'transaction_date': transaction.transaction_date.isoformat(),
                'supplier': supplier.name if supplier else None,
                'performed_by': performed_by.username if performed_by else None,
                'notes': transaction.notes,
                'items': items_data,
                'total_items': len(items_data)
            })
        
        return jsonify({
            'success': True,
            'transactions': transactions_data,
            'total_count': len(transactions_data),
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'transaction_type': transaction_type,
                'item_id': item_id
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/reports/cost-analysis', methods=['GET'])
@token_required
def get_cost_analysis_report(current_user_id):
    """Get inventory cost analysis report"""
    from models import InventoryItem, InventoryCategory, InventoryTransaction, InventoryTransactionItem
    from sqlalchemy import func
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Calculate current inventory value
        items = InventoryItem.query.filter_by(status='active').all()
        current_inventory_value = sum(
            (item.quantity or 0) * (item.unit_cost or 0) for item in items
        )
        
        # Calculate costs by transaction type
        transaction_query = db.session.query(
            InventoryTransaction.transaction_type,
            func.sum(InventoryTransactionItem.quantity * InventoryTransactionItem.unit_cost).label('total_cost')
        ).join(
            InventoryTransactionItem,
            InventoryTransactionItem.transaction_id == InventoryTransaction.id
        )
        
        # Apply date filters
        if start_date:
            transaction_query = transaction_query.filter(InventoryTransaction.transaction_date >= start_date)
        if end_date:
            transaction_query = transaction_query.filter(InventoryTransaction.transaction_date <= end_date)
        
        transaction_query = transaction_query.group_by(InventoryTransaction.transaction_type)
        
        transaction_costs = {row[0]: float(row[1] or 0) for row in transaction_query.all()}
        
        # Calculate costs by category
        category_costs = []
        categories = InventoryCategory.query.all()
        for category in categories:
            category_items = InventoryItem.query.filter_by(category_id=category.id, status='active').all()
            category_value = sum(
                (item.quantity or 0) * (item.unit_cost or 0) for item in category_items
            )
            
            if category_value > 0:
                category_costs.append({
                    'category_id': category.id,
                    'category_name': category.name,
                    'total_value': float(category_value),
                    'item_count': len(category_items)
                })
        
        # Sort by value
        category_costs.sort(key=lambda x: x['total_value'], reverse=True)
        
        return jsonify({
            'success': True,
            'cost_analysis': {
                'current_inventory_value': float(current_inventory_value),
                'transaction_costs': {
                    'receipts': transaction_costs.get('receipt', 0.0),
                    'usage': transaction_costs.get('usage', 0.0),
                    'adjustments': transaction_costs.get('adjustment', 0.0),
                    'transfers': transaction_costs.get('transfer', 0.0)
                },
                'category_breakdown': category_costs,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# BOOKING INTEGRATION ENDPOINTS
# ============================================================================

@api_bp.route('/admin/inventory/booking-reservation', methods=['POST'])
@token_required
def create_booking_reservation(current_user_id):
    """Reserve inventory for a booking"""
    from models import BookingInventoryReservation, InventoryItem, Booking
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        booking_id = data.get('booking_id')
        items = data.get('items', [])  # [{item_id, quantity}]
        
        if not booking_id or not items:
            return jsonify({'success': False, 'message': 'Booking ID and items are required'}), 400
        
        # Verify booking exists
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        reservations_created = []
        insufficient_items = []
        
        for item_data in items:
            item_id = item_data.get('item_id')
            quantity = item_data.get('quantity', 1)
            
            item = InventoryItem.query.get(item_id)
            if not item:
                continue
            
            # Check if sufficient quantity available
            if item.quantity < quantity:
                insufficient_items.append({
                    'item_id': item.id,
                    'item_name': item.name,
                    'requested': quantity,
                    'available': item.quantity or 0
                })
                continue
            
            # Create reservation
            reservation = BookingInventoryReservation(
                booking_id=booking_id,
                item_id=item_id,
                quantity_reserved=quantity,
                reservation_date=datetime.utcnow(),
                status='reserved'
            )
            
            db.session.add(reservation)
            reservations_created.append({
                'item_id': item.id,
                'item_name': item.name,
                'quantity_reserved': quantity
            })
        
        db.session.commit()
        
        response_data = {
            'success': True,
            'message': f'{len(reservations_created)} item(s) reserved successfully',
            'reservations': reservations_created
        }
        
        if insufficient_items:
            response_data['warnings'] = {
                'insufficient_stock': insufficient_items
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/booking-consumption', methods=['POST'])
@token_required
def record_booking_consumption(current_user_id):
    """Record inventory consumption for a booking checkout"""
    from models import BookingInventoryReservation, InventoryItem, InventoryTransaction, InventoryTransactionItem, Booking
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({'success': False, 'message': 'Booking ID is required'}), 400
        
        # Verify booking exists
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Get all reservations for this booking
        reservations = BookingInventoryReservation.query.filter_by(
            booking_id=booking_id,
            status='reserved'
        ).all()
        
        if not reservations:
            return jsonify({'success': False, 'message': 'No reservations found for this booking'}), 404
        
        # Create usage transaction
        transaction = InventoryTransaction(
            transaction_type='usage',
            transaction_date=datetime.utcnow(),
            performed_by=current_user_id,
            notes=f'Booking #{booking_id} checkout consumption'
        )
        db.session.add(transaction)
        db.session.flush()  # Get transaction ID
        
        consumed_items = []
        
        for reservation in reservations:
            item = InventoryItem.query.get(reservation.item_id)
            if not item:
                continue
            
            # Create transaction item
            trans_item = InventoryTransactionItem(
                transaction_id=transaction.id,
                item_id=item.id,
                quantity=reservation.quantity_reserved,
                unit_cost=item.unit_cost
            )
            db.session.add(trans_item)
            
            # Update item quantity
            item.quantity = (item.quantity or 0) - reservation.quantity_reserved
            
            # Update reservation status
            reservation.status = 'consumed'
            reservation.consumed_date = datetime.utcnow()
            
            consumed_items.append({
                'item_id': item.id,
                'item_name': item.name,
                'quantity_consumed': reservation.quantity_reserved,
                'remaining_quantity': item.quantity
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(consumed_items)} item(s) consumed successfully',
            'transaction_id': transaction.id,
            'consumed_items': consumed_items
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/booking-release', methods=['POST'])
@token_required
def release_booking_reservation(current_user_id):
    """Release inventory reservations for a cancelled booking"""
    from models import BookingInventoryReservation, Booking
    
    user = User.query.get(current_user_id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return jsonify({'success': False, 'message': 'Booking ID is required'}), 400
        
        # Verify booking exists
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Get all active reservations for this booking
        reservations = BookingInventoryReservation.query.filter_by(
            booking_id=booking_id,
            status='reserved'
        ).all()
        
        if not reservations:
            return jsonify({'success': True, 'message': 'No active reservations to release'})
        
        released_items = []
        
        for reservation in reservations:
            reservation.status = 'released'
            reservation.consumed_date = datetime.utcnow()  # Use as release date
            
            released_items.append({
                'item_id': reservation.item_id,
                'quantity_released': reservation.quantity_reserved
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(released_items)} reservation(s) released successfully',
            'released_items': released_items
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/inventory/check-availability', methods=['POST'])
@token_required
def check_inventory_availability(current_user_id):
    """Check if sufficient inventory is available for a booking"""
    from models import InventoryItem
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        items = data.get('items', [])  # [{item_id, quantity}]
        
        if not items:
            return jsonify({'success': False, 'message': 'Items list is required'}), 400
        
        availability_results = []
        all_available = True
        
        for item_data in items:
            item_id = item_data.get('item_id')
            quantity_needed = item_data.get('quantity', 1)
            
            item = InventoryItem.query.get(item_id)
            if not item:
                availability_results.append({
                    'item_id': item_id,
                    'available': False,
                    'reason': 'Item not found'
                })
                all_available = False
                continue
            
            available_quantity = item.quantity or 0
            is_available = available_quantity >= quantity_needed
            
            if not is_available:
                all_available = False
            
            availability_results.append({
                'item_id': item.id,
                'item_name': item.name,
                'quantity_needed': quantity_needed,
                'quantity_available': available_quantity,
                'available': is_available,
                'shortage': max(0, quantity_needed - available_quantity) if not is_available else 0
            })
        
        return jsonify({
            'success': True,
            'all_available': all_available,
            'items': availability_results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# PAYROLL API ENDPOINTS
# ============================================

@api_bp.route('/admin/payroll/generate', methods=['POST'])
@token_required
def generate_payroll(current_user_id):
    """Generate payroll for a staff member for a specific period (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        staff_id = data.get('staff_id')
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        
        if not staff_id or not period_start or not period_end:
            return jsonify({'success': False, 'message': 'Staff ID, period start, and period end are required'}), 400
        
        # Parse dates
        from datetime import datetime
        try:
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get staff member
        staff = User.query.get(staff_id)
        if not staff or not staff.is_staff:
            return jsonify({'success': False, 'message': 'Staff member not found'}), 404
        
        # Check if payroll already exists for this period
        existing = Payroll.query.filter_by(
            staff_id=staff_id,
            period_start=start_date,
            period_end=end_date
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Payroll already exists for this period'}), 400
        
        # Calculate hours from attendance records
        attendance_records = Attendance.query.filter(
            Attendance.user_id == staff_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
            Attendance.approved == True
        ).all()
        
        total_hours = sum(record.hours_worked for record in attendance_records)
        
        # Calculate regular hours (8 hours per day)
        days_worked = len(attendance_records)
        regular_hours = min(total_hours, days_worked * 8)
        overtime_hours = max(0, total_hours - regular_hours)
        
        # Calculate gross pay
        if staff.salary_type == 'fixed':
            gross_pay = staff.base_salary or 0.0
        else:  # hourly
            regular_pay = regular_hours * (staff.hourly_rate or 0.0)
            overtime_pay = overtime_hours * (staff.overtime_rate or staff.hourly_rate or 0.0)
            gross_pay = regular_pay + overtime_pay
        
        # Get bonuses and deductions from request
        bonuses = data.get('bonuses', [])
        deductions = data.get('deductions', [])
        
        total_bonuses = sum(float(b.get('amount', 0)) for b in bonuses)
        total_deductions = sum(float(d.get('amount', 0)) for d in deductions)
        
        # Calculate net pay
        net_pay = gross_pay + total_bonuses - total_deductions
        
        # Create payroll record
        payroll = Payroll(
            staff_id=staff_id,
            period_start=start_date,
            period_end=end_date,
            total_hours=total_hours,
            overtime_hours=overtime_hours,
            gross_pay=gross_pay,
            deductions=total_deductions,
            bonuses=total_bonuses,
            net_pay=net_pay,
            status='pending'
        )
        
        db.session.add(payroll)
        db.session.flush()  # Get payroll ID
        
        # Add bonus details
        for bonus in bonuses:
            bonus_record = PayrollBonus(
                payroll_id=payroll.id,
                description=bonus.get('description', ''),
                amount=float(bonus.get('amount', 0))
            )
            db.session.add(bonus_record)
        
        # Add deduction details
        for deduction in deductions:
            deduction_record = PayrollDeduction(
                payroll_id=payroll.id,
                description=deduction.get('description', ''),
                amount=float(deduction.get('amount', 0))
            )
            db.session.add(deduction_record)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payroll generated successfully',
            'payroll': {
                'id': payroll.id,
                'staff_id': payroll.staff_id,
                'staff_name': staff.username,
                'period_start': payroll.period_start.isoformat(),
                'period_end': payroll.period_end.isoformat(),
                'total_hours': payroll.total_hours,
                'overtime_hours': payroll.overtime_hours,
                'gross_pay': payroll.gross_pay,
                'bonuses': payroll.bonuses,
                'deductions': payroll.deductions,
                'net_pay': payroll.net_pay,
                'status': payroll.status,
                'date_issued': payroll.date_issued.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/payroll', methods=['GET'])
@token_required
def get_all_payroll(current_user_id):
    """Get all payroll records with filters (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Get query parameters
        staff_id = request.args.get('staff_id', type=int)
        status = request.args.get('status')
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')
        
        # Build query
        query = Payroll.query.filter_by(archived=False)
        
        if staff_id:
            query = query.filter_by(staff_id=staff_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if period_start:
            from datetime import datetime
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            query = query.filter(Payroll.period_start >= start_date)
        
        if period_end:
            from datetime import datetime
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
            query = query.filter(Payroll.period_end <= end_date)
        
        payrolls = query.order_by(Payroll.date_issued.desc()).all()
        
        result = []
        for payroll in payrolls:
            staff = User.query.get(payroll.staff_id)
            result.append({
                'id': payroll.id,
                'staff_id': payroll.staff_id,
                'staff_name': staff.username if staff else 'Unknown',
                'staff_role': staff.staff_role if staff else 'Unknown',
                'period_start': payroll.period_start.isoformat(),
                'period_end': payroll.period_end.isoformat(),
                'total_hours': payroll.total_hours,
                'overtime_hours': payroll.overtime_hours,
                'gross_pay': payroll.gross_pay,
                'bonuses': payroll.bonuses,
                'deductions': payroll.deductions,
                'net_pay': payroll.net_pay,
                'status': payroll.status,
                'date_issued': payroll.date_issued.isoformat()
            })
        
        return jsonify({
            'success': True,
            'payrolls': result,
            'total_records': len(result)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/payroll/<int:payroll_id>', methods=['GET'])
@token_required
def get_payroll_details(current_user_id, payroll_id):
    """Get detailed payroll information including bonuses and deductions (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        payroll = Payroll.query.get(payroll_id)
        if not payroll:
            return jsonify({'success': False, 'message': 'Payroll not found'}), 404
        
        staff = User.query.get(payroll.staff_id)
        
        # Get bonuses
        bonuses_list = [{
            'id': b.id,
            'description': b.description,
            'amount': b.amount
        } for b in payroll.bonuses_list]
        
        # Get deductions
        deductions_list = [{
            'id': d.id,
            'description': d.description,
            'amount': d.amount
        } for d in payroll.deductions_list]
        
        return jsonify({
            'success': True,
            'payroll': {
                'id': payroll.id,
                'staff_id': payroll.staff_id,
                'staff_name': staff.username if staff else 'Unknown',
                'staff_role': staff.staff_role if staff else 'Unknown',
                'staff_email': staff.email if staff else '',
                'period_start': payroll.period_start.isoformat(),
                'period_end': payroll.period_end.isoformat(),
                'total_hours': payroll.total_hours,
                'overtime_hours': payroll.overtime_hours,
                'gross_pay': payroll.gross_pay,
                'bonuses': payroll.bonuses,
                'bonuses_list': bonuses_list,
                'deductions': payroll.deductions,
                'deductions_list': deductions_list,
                'net_pay': payroll.net_pay,
                'status': payroll.status,
                'date_issued': payroll.date_issued.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/payroll/<int:payroll_id>/approve', methods=['POST'])
@token_required
def approve_payroll(current_user_id, payroll_id):
    """Approve a payroll record (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        payroll = Payroll.query.get(payroll_id)
        if not payroll:
            return jsonify({'success': False, 'message': 'Payroll not found'}), 404
        
        if payroll.status == 'paid':
            return jsonify({'success': False, 'message': 'Payroll already paid'}), 400
        
        payroll.status = 'approved'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payroll approved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/payroll/<int:payroll_id>/pay', methods=['POST'])
@token_required
def mark_payroll_paid(current_user_id, payroll_id):
    """Mark payroll as paid (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        payroll = Payroll.query.get(payroll_id)
        if not payroll:
            return jsonify({'success': False, 'message': 'Payroll not found'}), 404
        
        payroll.status = 'paid'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payroll marked as paid successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/staff/payroll', methods=['GET'])
@token_required
def get_my_payroll(current_user_id):
    """Get payroll records for the logged-in staff member"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Get query parameters
        period = request.args.get('period', 'current_month')
        
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        # Calculate date range based on period
        if period == 'current_month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start_date = last_day_last_month.replace(day=1)
            end_date = last_day_last_month
        elif period == 'last_3_months':
            start_date = (today - timedelta(days=90))
            end_date = today
        elif period == 'year_to_date':
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = today.replace(day=1)
            end_date = today
        
        # Get payroll records
        payrolls = Payroll.query.filter(
            Payroll.staff_id == current_user_id,
            Payroll.period_start >= start_date,
            Payroll.period_end <= end_date,
            Payroll.archived == False
        ).order_by(Payroll.date_issued.desc()).all()
        
        result = []
        for payroll in payrolls:
            # Get bonuses
            bonuses_list = [{
                'description': b.description,
                'amount': b.amount
            } for b in payroll.bonuses_list]
            
            # Get deductions
            deductions_list = [{
                'description': d.description,
                'amount': d.amount
            } for d in payroll.deductions_list]
            
            result.append({
                'id': payroll.id,
                'period_start': payroll.period_start.isoformat(),
                'period_end': payroll.period_end.isoformat(),
                'total_hours': payroll.total_hours,
                'overtime_hours': payroll.overtime_hours,
                'gross_pay': payroll.gross_pay,
                'bonuses': payroll.bonuses,
                'bonuses_list': bonuses_list,
                'deductions': payroll.deductions,
                'deductions_list': deductions_list,
                'net_pay': payroll.net_pay,
                'status': payroll.status,
                'date_issued': payroll.date_issued.isoformat()
            })
        
        return jsonify({
            'success': True,
            'payrolls': result,
            'total_records': len(result)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/staff/payroll/summary', methods=['GET'])
@token_required
def get_payroll_summary(current_user_id):
    """Get payroll summary for the logged-in staff member"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        # Current month
        current_month_start = today.replace(day=1)
        current_month_payroll = Payroll.query.filter(
            Payroll.staff_id == current_user_id,
            Payroll.period_start >= current_month_start,
            Payroll.archived == False
        ).first()
        
        # Year to date
        year_start = today.replace(month=1, day=1)
        ytd_payrolls = Payroll.query.filter(
            Payroll.staff_id == current_user_id,
            Payroll.period_start >= year_start,
            Payroll.archived == False
        ).all()
        
        ytd_total = sum(p.net_pay for p in ytd_payrolls)
        ytd_hours = sum(p.total_hours for p in ytd_payrolls)
        
        # Get current month attendance for estimated pay
        current_month_attendance = Attendance.query.filter(
            Attendance.user_id == current_user_id,
            Attendance.date >= current_month_start,
            Attendance.approved == True
        ).all()
        
        current_month_hours = sum(a.hours_worked for a in current_month_attendance)
        
        # Estimate current month pay
        if user.salary_type == 'fixed':
            estimated_pay = user.base_salary or 0.0
        else:
            estimated_pay = current_month_hours * (user.hourly_rate or 0.0)
        
        return jsonify({
            'success': True,
            'summary': {
                'current_month': {
                    'hours_worked': current_month_hours,
                    'estimated_pay': estimated_pay,
                    'payroll_generated': current_month_payroll is not None,
                    'net_pay': current_month_payroll.net_pay if current_month_payroll else 0.0,
                    'status': current_month_payroll.status if current_month_payroll else 'not_generated'
                },
                'year_to_date': {
                    'total_earnings': ytd_total,
                    'total_hours': ytd_hours,
                    'payroll_count': len(ytd_payrolls)
                },
                'staff_info': {
                    'salary_type': user.salary_type,
                    'base_salary': user.base_salary,
                    'hourly_rate': user.hourly_rate,
                    'overtime_rate': user.overtime_rate
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# SCHEDULE API ENDPOINTS
# ============================================

@api_bp.route('/admin/schedules', methods=['GET'])
@token_required
def get_schedules(current_user_id):
    """Get schedules for a specific date (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'success': False, 'message': 'Date parameter required'}), 400
        
        try:
            schedule_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        schedules = Schedule.query.filter_by(date=schedule_date).all()
        
        result = []
        for schedule in schedules:
            staff = User.query.get(schedule.staff_id)
            result.append({
                'id': schedule.id,
                'staff_id': schedule.staff_id,
                'staff_name': staff.username if staff else 'Unknown',
                'staff_role': staff.staff_role if staff else 'Unknown',
                'date': schedule.date.isoformat(),
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
                'shift': schedule.shift,
                'notes': schedule.notes,
                'created_at': schedule.created_at.isoformat() if schedule.created_at else None
            })
        
        return jsonify({
            'success': True,
            'schedules': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/schedules', methods=['POST'])
@token_required
def create_schedule(current_user_id):
    """Create a new schedule (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        staff_id = data.get('staff_id')
        date_str = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        shift = data.get('shift')
        notes = data.get('notes', '')
        
        if not all([staff_id, date_str, start_time_str, end_time_str, shift]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Validate staff exists
        staff = User.query.get(staff_id)
        if not staff or not staff.is_staff:
            return jsonify({'success': False, 'message': 'Staff member not found'}), 404
        
        # Parse date and times
        try:
            schedule_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date or time format'}), 400
        
        # Check for conflicts
        existing = Schedule.query.filter_by(
            staff_id=staff_id,
            date=schedule_date
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Staff already has a schedule for this date'}), 400
        
        # Create schedule
        schedule = Schedule(
            staff_id=staff_id,
            date=schedule_date,
            start_time=start_time,
            end_time=end_time,
            shift=shift,
            notes=notes,
            created_by=current_user_id
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule created successfully',
            'schedule': {
                'id': schedule.id,
                'staff_id': schedule.staff_id,
                'staff_name': staff.username,
                'date': schedule.date.isoformat(),
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
                'shift': schedule.shift,
                'notes': schedule.notes
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/schedules/<int:schedule_id>', methods=['DELETE'])
@token_required
def delete_schedule(current_user_id, schedule_id):
    """Delete a schedule (Admin only)"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({'success': False, 'message': 'Schedule not found'}), 404
        
        db.session.delete(schedule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/staff/schedule', methods=['GET'])
@token_required
def get_my_schedule(current_user_id):
    """Get schedule for the logged-in staff member"""
    try:
        user = User.query.get(current_user_id)
        if not user or not user.is_staff:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Get upcoming schedules (next 7 days)
        today = datetime.now().date()
        end_date = today + timedelta(days=7)
        
        schedules = Schedule.query.filter(
            Schedule.staff_id == current_user_id,
            Schedule.date >= today,
            Schedule.date <= end_date
        ).order_by(Schedule.date).all()
        
        result = []
        for schedule in schedules:
            result.append({
                'id': schedule.id,
                'date': schedule.date.isoformat(),
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
                'shift': schedule.shift,
                'notes': schedule.notes
            })
        
        return jsonify({
            'success': True,
            'schedules': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# SERVICE REQUEST ENDPOINTS (Extra Services)
# ============================================

@api_bp.route('/service-requests', methods=['POST'])
@token_required
def create_service_request(current_user_id):
    """Create service request for extra services"""
    try:
        from models import ServiceRequest, InventoryItem
        
        data = request.get_json()
        booking_id = data.get('booking_id')
        services = data.get('services', [])  # List of {item_id, quantity}
        
        if not booking_id or not services:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Verify booking belongs to user
        booking = Booking.query.filter_by(id=booking_id, user_id=current_user_id).first()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        created_requests = []
        
        for service in services:
            item_id = service.get('item_id')
            quantity = service.get('quantity', 0)
            
            if quantity <= 0 or quantity > 10:
                continue
            
            # Get inventory item
            item = InventoryItem.query.get(item_id)
            if not item:
                continue
            
            # Check stock availability
            if item.current_stock < quantity:
                return jsonify({
                    'success': False,
                    'message': f'{item.name} is out of stock or insufficient quantity'
                }), 400
            
            # Create service request
            unit_price = item.unit_cost or 0
            service_request = ServiceRequest(
                booking_id=booking_id,
                user_id=current_user_id,
                inventory_item_id=item_id,
                quantity=quantity,
                unit_price=unit_price,
                total_fee=quantity * unit_price,
                status='pending'
            )
            
            db.session.add(service_request)
            created_requests.append({
                'item_name': item.name,
                'quantity': quantity,
                'total_fee': quantity * unit_price
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service requests created successfully',
            'requests': created_requests
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/service-requests/booking/<int:booking_id>', methods=['GET'])
@token_required
def get_booking_service_requests(current_user_id, booking_id):
    """Get all service requests for a booking"""
    try:
        from models import ServiceRequest
        
        # Verify booking belongs to user or user is admin
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        user = User.query.get(current_user_id)
        if booking.user_id != current_user_id and not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        requests = ServiceRequest.query.filter_by(booking_id=booking_id).all()
        
        return jsonify({
            'success': True,
            'service_requests': [{
                'id': req.id,
                'item_name': req.inventory_item.name if req.inventory_item else 'Unknown',
                'quantity': req.quantity,
                'unit_price': req.unit_price,
                'total_fee': req.total_fee,
                'status': req.status,
                'requested_at': req.requested_at.isoformat() if req.requested_at else None
            } for req in requests]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/service-requests', methods=['GET'])
@token_required
def get_all_service_requests(current_user_id):
    """Get all service requests (admin only)"""
    try:
        from models import ServiceRequest
        
        user = User.query.get(current_user_id)
        if not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        status_filter = request.args.get('status')
        
        query = ServiceRequest.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        requests = query.order_by(ServiceRequest.requested_at.desc()).all()
        
        return jsonify({
            'success': True,
            'service_requests': [{
                'id': req.id,
                'booking_id': req.booking_id,
                'guest_name': req.user.username if req.user else 'Unknown',
                'room_number': req.booking.room.room_number if req.booking and req.booking.room else 'N/A',
                'item_name': req.inventory_item.name if req.inventory_item else 'Unknown',
                'quantity': req.quantity,
                'total_fee': req.total_fee,
                'status': req.status,
                'requested_at': req.requested_at.isoformat() if req.requested_at else None
            } for req in requests]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/service-requests/<int:request_id>/status', methods=['PUT'])
@token_required
def update_service_request_status(current_user_id, request_id):
    """Update service request status (admin only)"""
    try:
        from models import ServiceRequest, InventoryTransaction
        
        user = User.query.get(current_user_id)
        if not user.is_admin:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        admin_notes = data.get('admin_notes', '')
        
        if new_status not in ['pending', 'in_progress', 'confirmed', 'failed']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        service_request = ServiceRequest.query.get(request_id)
        if not service_request:
            return jsonify({'success': False, 'message': 'Service request not found'}), 404
        
        old_status = service_request.status
        service_request.status = new_status
        service_request.admin_notes = admin_notes
        service_request.processed_by = current_user_id
        
        # If confirmed, deduct from inventory
        if new_status == 'confirmed' and old_status != 'confirmed':
            item = service_request.inventory_item
            if item.current_stock < service_request.quantity:
                return jsonify({
                    'success': False,
                    'message': 'Insufficient inventory stock'
                }), 400
            
            # Deduct inventory
            item.current_stock -= service_request.quantity
            
            # Create inventory transaction
            transaction = InventoryTransaction(
                item_id=item.id,
                transaction_type='out',
                quantity=service_request.quantity,
                reference_type='service_request',
                reference_id=service_request.id,
                notes=f'Service request for booking #{service_request.booking_id}',
                performed_by=current_user_id
            )
            db.session.add(transaction)
            
            service_request.confirmed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service request status updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/inventory/available-services', methods=['GET'])
@token_required
def get_available_services(current_user_id):
    """Get inventory items available as extra services"""
    try:
        from models import InventoryItem
        
        # Get items that can be offered as services (e.g., category = 'Guest Amenities')
        items = InventoryItem.query.filter(
            InventoryItem.current_stock >= 0,
            InventoryItem.status == 'active'
        ).all()
        
        return jsonify({
            'success': True,
            'services': [{
                'id': item.id,
                'name': item.name,
                'description': item.name,  # Use name as description since model doesn't have description field
                'unit_price': item.unit_cost or 0,
                'available_quantity': int(item.current_stock),
                'unit': item.unit_of_measure,
                'category': item.category.name if item.category else 'Other'
            } for item in items]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
