
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import jwt
import os
import random
from datetime import datetime, timedelta
from models import User, Room, Rating
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Create API blueprint
api_bp = Blueprint('email_verification_api', __name__, url_prefix='/api')

# Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'hotelmanagementsystem48@gmail.com')

def send_verification_email(email, verification_code):
    """Send verification email using SendGrid"""
    try:
        print(f"[EMAIL] Sending verification email to: {email}")
        print(f"[EMAIL] Verification code: {verification_code}")
        
        if not SENDGRID_API_KEY:
            print("[EMAIL] No SendGrid API key configured")
            return False
        
        # Create email content
        subject = "Easy Hotel - Email Verification Code"
        
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
        
        text_content = f"""
        Welcome to Easy Hotel!
        
        Your verification code is: {verification_code}
        
        Please enter this code in the app to complete your registration.
        This code will expire in 15 minutes.
        
        If you did not request this registration, please ignore this email.
        
        Best regards,
        Easy Hotel Team
        """
        
        # Create SendGrid message
        message = Mail(
            from_email='hotelmanagementsystem48@gmail.com',
            to_emails=email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content
        )
        
        # Send email
        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"[EMAIL] SendGrid response: {response.status_code}")
        
        if response.status_code == 202:
            print("[EMAIL] ✅ Email sent successfully!")
            return True
        else:
            print(f"[EMAIL] ❌ Failed to send email: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[EMAIL] ❌ Error sending email: {str(e)}")
        return False

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register new user with email verification"""
    try:
        data = request.get_json()
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        phone_number = data.get('phone_number')
        verification_code = data.get('verification_code')
        
        print(f"[REGISTER] Registration attempt for: {email}")
        print(f"[REGISTER] Has verification code: {bool(verification_code)}")
        
        # If verification code is provided, verify it
        if verification_code:
            print(f"[REGISTER] Verifying code: {verification_code}")
            
            # Find user with this email and verification code
            user = User.query.filter_by(
                email=email, 
                verification_code=verification_code,
                is_verified=False
            ).first()
            
            if not user:
                print(f"[REGISTER] Invalid verification code for: {email}")
                return jsonify({
                    'success': False, 
                    'message': 'Invalid verification code'
                }), 400
            
            # Verify the user
            user.is_verified = True
            user.verification_code = None
            db.session.commit()
            
            print(f"[REGISTER] ✅ User verified successfully: {email}")
            
            return jsonify({
                'success': True,
                'message': 'Email verified successfully! You can now login.',
                'user_id': user.id
            }), 200
        
        # Initial registration (no verification code provided)
        print(f"[REGISTER] Initial registration for: {email}")
        
        # Basic validation
        if not all([username, email, password]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check if user exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                return jsonify({'success': False, 'message': 'Username already taken'}), 400
            else:
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Generate verification code
        code = str(random.randint(100000, 999999))
        
        # Create new user (unverified)
        new_user = User(
            username=username,
            email=email,
            phone_number=phone_number,
            is_verified=False,
            verification_code=code
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"[REGISTER] User created with ID: {new_user.id}")
        
        # Send verification email
        email_sent = send_verification_email(email, code)
        
        if email_sent:
            return jsonify({
                'success': True,
                'message': 'Registration successful! Please check your email for verification code.',
                'requires_verification': True,
                'user_id': new_user.id
            }), 201
        else:
            # If email fails, still allow registration but notify user
            return jsonify({
                'success': True,
                'message': 'Registration successful! Email verification temporarily unavailable.',
                'requires_verification': False,
                'user_id': new_user.id
            }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[REGISTER] Error: {str(e)}")
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        print(f"[LOGIN] Login attempt for: {email}")
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            print(f"[LOGIN] Invalid credentials for: {email}")
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        if not user.is_verified:
            print(f"[LOGIN] Email not verified for: {email}")
            return jsonify({
                'success': False, 
                'message': 'Please verify your email before logging in',
                'requires_verification': True
            }), 401
        
        # Generate JWT token
        token_payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        
        token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        print(f"[LOGIN] ✅ Login successful for: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        }), 200
        
    except Exception as e:
        print(f"[LOGIN] Error: {str(e)}")
        return jsonify({'success': False, 'message': f'Login failed: {str(e)}'}), 500

@api_bp.route('/auth/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email required'}), 400
        
        user = User.query.filter_by(email=email, is_verified=False).first()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found or already verified'}), 404
        
        # Generate new verification code
        code = str(random.randint(100000, 999999))
        user.verification_code = code
        db.session.commit()
        
        # Send verification email
        email_sent = send_verification_email(email, code)
        
        if email_sent:
            return jsonify({
                'success': True,
                'message': 'Verification code sent to your email'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send verification email'
            }), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to resend: {str(e)}'}), 500

@api_bp.route('/rooms', methods=['GET'])
def get_rooms():
    """Get all rooms with ratings"""
    try:
        rooms = Room.query.all()
        room_list = []
        
        for room in rooms:
            # Calculate average rating
            ratings = Rating.query.filter_by(room_id=room.id).all()
            avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
            
            room_data = {
                'id': room.id,
                'name': room.name,
                'description': room.description,
                'price_per_night': room.price_per_night,
                'capacity': room.capacity,
                'averageRating': round(avg_rating, 1),
                'reviewCount': len(ratings),
                'stars': '★' * int(avg_rating) if avg_rating > 0 else '',
                'image_url': getattr(room, 'image_url', ''),
                'room_type': getattr(room, 'room_type', 'Standard')
            }
            room_list.append(room_data)
        
        return jsonify({'data': room_list}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get rooms: {str(e)}'}), 500

@api_bp.route('/rooms/ratings', methods=['GET'])
def get_room_ratings():
    """Get room ratings summary"""
    try:
        rooms = Room.query.all()
        ratings_data = []
        
        for room in rooms:
            ratings = Rating.query.filter_by(room_id=room.id).all()
            avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
            
            ratings_data.append({
                'room_id': room.id,
                'room_name': room.name,
                'average_rating': round(avg_rating, 1),
                'review_count': len(ratings),
                'stars': '★' * int(avg_rating) if avg_rating > 0 else ''
            })
        
        return jsonify({'ratings': ratings_data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get ratings: {str(e)}'}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API with email verification is working',
        'timestamp': datetime.utcnow().isoformat(),
        'email_configured': bool(SENDGRID_API_KEY)
    }), 200
# Import payment service
try:
    from payment_service import gcash_service
    from models import Payment, Booking
    PAYMENT_SERVICE_AVAILABLE = True
    print("✅ Payment service imported successfully")
except ImportError as e:
    print(f"⚠️ Payment service not available: {e}")
    PAYMENT_SERVICE_AVAILABLE = False

# Payment Routes
@api_bp.route('/payment/methods', methods=['GET'])
def get_payment_methods():
    """Get available payment methods"""
    try:
        # Return basic payment methods
        payment_methods = [
            {
                'id': 1,
                'name': 'GCash',
                'code': 'gcash',
                'is_online': True,
                'description': 'Pay securely with GCash',
                'icon_url': '/static/images/gcash-icon.png'
            },
            {
                'id': 2,
                'name': 'Cash',
                'code': 'cash',
                'is_online': False,
                'description': 'Pay with cash at the hotel',
                'icon_url': '/static/images/cash-icon.png'
            }
        ]
        
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
        if not PAYMENT_SERVICE_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'Payment service temporarily unavailable'
            }), 503
        
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
        print(f"   Phone: {phone_number}")
        
        # Check if booking already has a completed payment
        completed_payment = Payment.query.filter(
            Payment.booking_id == booking_id,
            Payment.payment_status == 'completed'
        ).first()
        
        if completed_payment and booking.payment_status not in ['refunded', 'pending']:
            return jsonify({'success': False, 'message': 'Booking already paid'}), 400
        
        # Delete any existing pending payment
        pending_payment = Payment.query.filter_by(
            booking_id=booking_id, 
            payment_status='pending'
        ).first()
        
        if pending_payment:
            db.session.delete(pending_payment)
            db.session.commit()
        
        # Calculate downpayment (30% of total price)
        downpayment_amount = booking.total_price * 0.30
        
        # Create GCash payment
        result = gcash_service.create_gcash_payment_intent(
            booking_id=booking_id,
            amount=downpayment_amount,
            user_phone=phone_number
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'payment_id': result['payment_id'],
                'payment_intent_id': result['payment_intent_id'],
                'client_key': result.get('client_key'),
                'redirect_url': result.get('redirect_url'),
                'amount': downpayment_amount,
                'total_amount': booking.total_price,
                'remaining_balance': booking.total_price - downpayment_amount
            })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Payment creation error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@api_bp.route('/payment/<int:payment_id>/verify', methods=['POST'])
@token_required
def verify_payment(current_user_id, payment_id):
    """Verify payment status"""
    try:
        if not PAYMENT_SERVICE_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'Payment verification temporarily unavailable'
            }), 503
        
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
            <a href="#" class="btn" onclick="window.close()">Close</a>
        </div>
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
            .btn { background: #f44336; color: white; padding: 12px 24px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="error-card">
            <div class="error-icon">❌</div>
            <h2>Payment Failed</h2>
            <p>Your payment could not be processed at this time.</p>
            <p>Please try again or contact support.</p>
            <a href="#" class="btn" onclick="window.close()">Close</a>
        </div>
    </body>
    </html>
    """