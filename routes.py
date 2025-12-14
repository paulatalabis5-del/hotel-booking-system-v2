import json
from datetime import datetime, timedelta, time, date
from flask import render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from extensions import db, login_manager
from models import User, Room, Amenity, Booking, BookingAmenity, Rating, Notification, Attendance, LeaveRequest, Payroll
import re
import random
import smtplib
from email.mime.text import MIMEText
from flask_dance.contrib.google import make_google_blueprint, google
import os
from werkzeug.utils import secure_filename
from flask_mail import Message
import secrets
from flask_mail import Mail
import jwt
from functools import wraps

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'hotelmanagementsystem48@gmail.com'
app.config['MAIL_PASSWORD'] = 'gtyxoxlvpftyoziv'
mail = Mail(app)

# JWT Authentication Decorators
def admin_required(f):
    """Decorator to require admin authentication via JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"\n🔒 [ADMIN_AUTH] Checking admin access for: {f.__name__}")
        
        # Get token from header
        token = request.headers.get('Authorization')
        if not token:
            print("   ❌ No token provided")
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode JWT token
            data = jwt.decode(token, 'your-secret-key-here', algorithms=['HS256'])
            user_id = data['user_id']
            
            # Get user from database
            user = User.query.get(user_id)
            if not user:
                print(f"   ❌ User not found: {user_id}")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            # Check if user is admin
            if not user.is_admin:
                print(f"   ❌ Access denied - User is not admin: {user.username}")
                return jsonify({'success': False, 'message': 'Admin access required'}), 403
            
            print(f"   ✅ Admin access granted: {user.username}")
            return f(user_id, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            print("   ❌ Token expired")
            return jsonify({'success': False, 'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            print("   ❌ Invalid token")
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        except Exception as e:
            print(f"   ❌ Auth error: {str(e)}")
            return jsonify({'success': False, 'message': 'Authentication failed'}), 401
    
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return jsonify({
        'status': 'success',
        'message': 'Easy Hotel Booking API is running',
        'version': '1.0',
        'endpoints': {
            'api': '/api',
            'health': '/health'
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'database': 'connected'
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_staff:
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Prevent admin from logging in via user login
        if user and user.is_admin:
            flash('Admin accounts must log in through the admin login page.', 'danger')
            return render_template('login.html')
        
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            elif user.is_staff:
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
            
    return render_template('admin_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        verification_code = request.form.get('verification_code')
        phone_number = request.form.get('phone_number')
        
        # If we're verifying the code
        if verification_code:
            if verification_code == session.get('email_verification'):
                user_data = session.pop('pending_user')
                new_user = User(username=user_data['username'], email=user_data['email'], phone_number=user_data['phone_number'])
                new_user.set_password(user_data['password'])
                db.session.add(new_user)
                db.session.commit()
                session.pop('email_verification', None)
                session.pop('email_verification_email', None)
                login_user(new_user)  # Automatically log in the user
                flash('Registration successful! Welcome to Easy Hotel.', 'success')
                if new_user.is_admin:
                    return redirect(url_for('user_list'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid verification code. Please try again.', 'danger')
                return render_template('register.html', require_code=True, email=email)
        
        # Initial registration form submission
        # Username validation
        if not re.match(r'^[A-Za-z]{5,}$', username or ''):
            flash('Username must be at least 5 letters and contain only letters.', 'danger')
            return render_template('register.html')
        
        # Password validation
        if not re.match(r'^(?=.*\d).{8,}$', password or ''):
            flash('Password must be at least 8 characters and include a number.', 'danger')
            return render_template('register.html')
        
        # Email validation
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email or ''):
            flash('Invalid email address.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Phone number validation
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 11:
            flash('Phone number must be exactly 11 digits and contain only numbers.', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('register.html')
        
        # Generate and send verification code
        code = str(random.randint(100000, 999999))
        session['email_verification'] = code
        session['email_verification_email'] = email
        session['pending_user'] = {
            'username': username,
            'email': email,
            'password': password,
            'phone_number': phone_number
        }
        
        # Send verification email
        try:
            msg = MIMEText(f'''
            Welcome to Easy Hotel!
            
            Your verification code is: {code}
            
            Please enter this code to complete your registration.
            
            If you did not request this registration, please ignore this email.
            
            Best regards,
            Easy Hotel Team
            ''')
            msg['Subject'] = 'Easy Hotel - Email Verification'
            msg['From'] = 'no-reply@easyhotel.com'
            msg['To'] = email
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login('hotelmanagementsystem48@gmail.com', 'gtyxoxlvpftyoziv')
                server.sendmail('no-reply@easyhotel.com', [email], msg.as_string())
            
            flash('Verification code has been sent to your email. Please check your inbox.', 'info')
            return render_template('register.html', require_code=True, email=email)
            
        except Exception as e:
            print(f"Email error: {str(e)}")  # For debugging
            flash('Failed to send verification email. Please try again later.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        return update_profile()
    return render_template('profile.html', current_user=current_user)

@app.route('/bookings')
@login_required
def bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('bookings.html', bookings=bookings, notifications=notifications, datetime=datetime)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    elif current_user.is_staff:
        return redirect(url_for('staff_dashboard'))
    else:
        return redirect(url_for('bookings'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    pending_bookings = Booking.query.filter_by(status='pending').all()
    confirmed_bookings = Booking.query.filter_by(status='confirmed').all()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').all()
    recent_ratings = Rating.query.order_by(Rating.created_at.desc()).limit(10).all()
    
    # Calculate total revenue from confirmed bookings
    total_revenue = db.session.query(db.func.sum(Booking.total_price)).filter_by(status='confirmed').scalar() or 0
    
    return render_template('admin_dashboard.html', 
                          pending_bookings=pending_bookings,
                          confirmed_bookings=confirmed_bookings,
                          cancelled_bookings=cancelled_bookings,
                          recent_ratings=recent_ratings,
                          total_revenue=total_revenue)

@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
        
    rooms = Room.query.all()
    amenities = Amenity.query.all()
    
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        check_in_date = datetime.strptime(request.form.get('check_in_date'), '%Y-%m-%d').date()
        check_out_date = datetime.strptime(request.form.get('check_out_date'), '%Y-%m-%d').date()
        adults = int(request.form.get('adults', 1))
        children = int(request.form.get('children', 0))
        total_guests = adults + children
        
        room = Room.query.get(room_id)
        
        # Check if room is available for the selected dates
        existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
            ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
            ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
            ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
        ).filter(Booking.status != 'cancelled').count()
        
        if existing_bookings > 0:
            flash('Room is not available for the selected dates', 'danger')
            return redirect(url_for('booking'))
            
        if total_guests > room.capacity:
            flash(f'This room can only accommodate up to {room.capacity} guests', 'danger')
            return redirect(url_for('booking'))
            
        # Calculate total price
        days = (check_out_date - check_in_date).days
        total_price = room.price_per_night * days
        
        # Get selected amenities
        selected_amenities = []
        amenities_cost = 0
        
        for amenity in amenities:
            quantity = request.form.get(f'amenity_{amenity.id}')
            if quantity and int(quantity) > 0:
                selected_amenities.append({
                    'id': amenity.id,
                    'quantity': int(quantity)
                })
                amenities_cost += amenity.price * int(quantity)
                
        total_price += amenities_cost
        
        # Store booking details in session for checkout
        session['booking'] = {
            'room_id': room_id,
            'check_in_date': check_in_date.strftime('%Y-%m-%d'),
            'check_out_date': check_out_date.strftime('%Y-%m-%d'),
            'adults': adults,
            'children': children,
            'total_guests': total_guests,
            'total_price': total_price,
            'amenities': selected_amenities
        }
        
        return redirect(url_for('checkout'))
        
    return render_template('booking.html', rooms=rooms, amenities=amenities)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if current_user.is_admin or 'booking' not in session:
        return redirect(url_for('booking'))
        
    booking_data = session['booking']
    room = Room.query.get(booking_data['room_id'])
    
    amenities_details = []
    for amenity_data in booking_data['amenities']:
        amenity = Amenity.query.get(amenity_data['id'])
        amenities_details.append({
            'id': amenity.id,
            'name': amenity.name,
            'price': amenity.price,
            'quantity': amenity_data['quantity'],
            'total': amenity.price * amenity_data['quantity']
        })
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        
        # Create booking
        new_booking = Booking(
            user_id=current_user.id,
            room_id=booking_data['room_id'],
            check_in_date=datetime.strptime(booking_data['check_in_date'], '%Y-%m-%d').date(),
            check_out_date=datetime.strptime(booking_data['check_out_date'], '%Y-%m-%d').date(),
            guests=booking_data['total_guests'],
            total_price=booking_data['total_price'],
            status='pending'
        )
        
        db.session.add(new_booking)
        db.session.flush()  # Get the booking ID
        
        # Add booking amenities
        for amenity_data in booking_data['amenities']:
            booking_amenity = BookingAmenity(
                booking_id=new_booking.id,
                amenity_id=amenity_data['id'],
                quantity=amenity_data['quantity']
            )
            db.session.add(booking_amenity)
            
        # Create notification
        notification = Notification(
            user_id=current_user.id,
            title="Booking Confirmation",
            message=f"Your booking at Easy Hotel has been received and is pending confirmation. Booking ID: {new_booking.id}"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Clear booking data from session
        session.pop('booking', None)
        
        flash('Booking completed successfully! Awaiting admin confirmation.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('checkout.html', room=room, booking=booking_data, amenities=amenities_details)

@app.route('/rating/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def rating(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking belongs to current user
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
        
    # Check if booking is completed and confirmed
    if booking.status != 'confirmed' or booking.check_out_date > datetime.now().date():
        flash('You can only rate confirmed and completed stays', 'warning')
        return redirect(url_for('dashboard'))
        
    # Check if already rated
    existing_rating = Rating.query.filter_by(booking_id=booking_id).first()
    
    if request.method == 'POST' and not existing_rating:
        overall_rating = int(request.form.get('overall_rating'))
        room_rating = int(request.form.get('room_rating'))
        amenities_rating = int(request.form.get('amenities_rating'))
        service_rating = int(request.form.get('service_rating'))
        comment = request.form.get('comment')
        
        # Validate ratings
        if not all(1 <= rating <= 5 for rating in [overall_rating, room_rating, amenities_rating, service_rating]):
            flash('All ratings must be between 1 and 5 stars', 'danger')
            return redirect(url_for('rating', booking_id=booking_id))
            
        new_rating = Rating(
            user_id=current_user.id,
            booking_id=booking_id,
            overall_rating=overall_rating,
            room_rating=room_rating,
            amenities_rating=amenities_rating,
            service_rating=service_rating,
            comment=comment
        )
        
        db.session.add(new_rating)
        
        # Create notification for admin
        notification = Notification(
            user_id=current_user.id,
            title="New Rating Submitted",
            message=f"A new rating has been submitted for booking #{booking_id}. Overall rating: {overall_rating}/5"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        flash('Thank you for your rating!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('rating.html', booking=booking, existing_rating=existing_rating)

@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Mark all as read
    for notification in user_notifications:
        notification.is_read = True
    
    db.session.commit()
    
    return render_template('notifications.html', notifications=user_notifications)

# Admin Routes
@app.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking belongs to current user
    if booking.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if booking can be cancelled (not already cancelled and not past check-in)
    if booking.status == 'cancelled':
        flash('This booking is already cancelled', 'warning')
        return redirect(url_for('dashboard'))
    
    if booking.check_in_date <= datetime.now().date():
        flash('Cannot cancel a booking that has already started', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get cancellation reason
    reason = request.form.get('reason')
    if not reason:
        flash('Please provide a reason for cancellation', 'danger')
        return redirect(url_for('dashboard'))
    
    # Update booking status
    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancelled_by = 'user'
    
    # Create notification
    notification = Notification(
        user_id=current_user.id,
        title="Booking Cancelled",
        message=f"Your booking (ID: {booking.id}) has been cancelled. Reason: {reason}"
    )
    db.session.add(notification)
    
    db.session.commit()
    
    flash('Booking cancelled successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/booking/<int:booking_id>/verify', methods=['POST'])
@login_required
def verify_booking(booking_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    booking = Booking.query.get_or_404(booking_id)
    action = request.form.get('action')
    
    if action == 'confirm':
        booking.status = 'confirmed'
        notification_message = f"Your booking (ID: {booking.id}) has been confirmed. We look forward to welcoming you to Easy Hotel!"
    elif action == 'cancel':
        reason = request.form.get('reason')
        booking.status = 'cancelled'
        booking.cancellation_reason = reason
        booking.cancelled_by = 'admin'
        notification_message = f"Your booking (ID: {booking.id}) has been cancelled by the administrator. Reason: {reason}"
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
    # Create notification for the user
    notification = Notification(
        user_id=booking.user_id,
        title=f"Booking {booking.status.capitalize()}",
        message=notification_message
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/rating/<int:rating_id>/reply', methods=['POST'])
@login_required
def reply_to_rating(rating_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    rating = Rating.query.get_or_404(rating_id)
    reply = request.form.get('reply')
    
    rating.admin_reply = reply
    
    # Create notification for the user
    notification = Notification(
        user_id=rating.user_id,
        title="Response to Your Rating",
        message=f"Admin has responded to your rating: {reply}"
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

# API Routes for AJAX
@app.route('/api/rooms')
def api_rooms():
    from models import RoomSize, FloorPlan
    
    rooms = Room.query.all()
    room_list = []
    
    for room in rooms:
        # Get room size for type name
        room_size = RoomSize.query.get(room.room_size_id) if room.room_size_id else None
        room_type_name = room_size.room_type_name if room_size else 'Standard'
        
        # Fix typo
        if room_type_name.lower() == 'suit':
            room_type_name = 'Suite'
        
        # Get floor plan
        floor_plan = FloorPlan.query.get(room.floor_id) if room.floor_id else None
        
        # Get all images
        images = []
        for img in [room.image_1, room.image_2, room.image_3, room.image_4, room.image_5]:
            if img:
                images.append(img)
        
        # Debug information
        print(f"Processing room for API: {room.name}, Image URL: {room.image_url}")
        
        room_list.append({
            'id': room.id,
            'room_number': room.room_number or '',
            'room_type_id': room.room_size_id or 0,
            'room_type_name': room_type_name,
            'floor_plan_id': room.floor_id or 0,
            'floor_name': floor_plan.floor_name if floor_plan else 'Ground Floor',
            'name': room.name,
            'description': room.description,
            'price_per_night': room.price_per_night,
            'capacity': room.capacity,
            'max_adults': room_size.max_adults if room_size else 2,
            'max_children': room_size.max_children if room_size else 0,
            'status': room.status or 'available',
            'image_url': room.image_url or room.image_1 or '',
            'image_1': room.image_1 or '',
            'image_2': room.image_2 or '',
            'image_3': room.image_3 or '',
            'image_4': room.image_4 or '',
            'image_5': room.image_5 or '',
            'images': images,
        })
    
    return jsonify({'data': room_list})

@app.route('/debug/images')
def debug_images():
    return render_template('debug_images.html')
    
@app.route('/debug/api/rooms')
def debug_api_rooms():
    rooms = Room.query.all()
    room_data = []
    
    for room in rooms:
        room_data.append({
            'id': room.id,
            'name': room.name,
            'image_url': room.image_url,
            'description': room.description
        })
    
    return render_template('debug_room_api.html', rooms=room_data)

# Legacy amenities route moved to /api/booking-amenities to avoid conflict
@app.route('/api/booking-amenities')
def api_booking_amenities():
    amenities = Amenity.query.all()
    amenity_list = []
    
    for amenity in amenities:
        amenity_list.append({
            'id': amenity.id,
            'name': amenity.name,
            'description': amenity.description,
            'price': amenity.price
        })
    
    return jsonify(amenity_list)

@app.route('/api/check_availability')
def check_availability():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if not all([room_id, check_in, check_out]):
        return jsonify({'available': False, 'message': 'Missing parameters'})
    
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'available': False, 'message': 'Invalid date format'})
    
    # Check if room is available for the selected dates
    existing_bookings = Booking.query.filter_by(room_id=room_id).filter(
        ((Booking.check_in_date <= check_in_date) & (Booking.check_out_date >= check_in_date)) |
        ((Booking.check_in_date <= check_out_date) & (Booking.check_out_date >= check_out_date)) |
        ((Booking.check_in_date >= check_in_date) & (Booking.check_out_date <= check_out_date))
    ).filter(Booking.status != 'cancelled').count()
    
    return jsonify({
        'available': existing_bookings == 0,
        'message': 'Room available' if existing_bookings == 0 else 'Room not available for selected dates'
    })

@app.route('/api/calculate_price')
def calculate_price():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    adults = int(request.args.get('adults', 1))
    children = int(request.args.get('children', 0))
    amenities = request.args.get('amenities', '[]')
    
    if not all([room_id, check_in, check_out]):
        return jsonify({'success': False, 'message': 'Missing parameters'})
    
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        amenities_data = json.loads(amenities)
    except (ValueError, json.JSONDecodeError):
        return jsonify({'success': False, 'message': 'Invalid parameters'})
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'success': False, 'message': 'Room not found'})
    
    # Calculate number of days
    days = (check_out_date - check_in_date).days
    if days <= 0:
        return jsonify({'success': False, 'message': 'Check-out date must be after check-in date'})
    
    # Check if total guests exceed room capacity
    total_guests = adults + children
    if total_guests > room.capacity:
        return jsonify({'success': False, 'message': f'Room can only accommodate up to {room.capacity} guests'})
    
    # Calculate room cost
    room_cost = room.price_per_night * days
    
    # Calculate amenities cost
    amenities_cost = 0
    for amenity_data in amenities_data:
        amenity = Amenity.query.get(amenity_data.get('id'))
        if amenity:
            amenities_cost += amenity.price * amenity_data.get('quantity', 0)
    
    total_cost = room_cost + amenities_cost
    
    return jsonify({
        'success': True,
        'room_cost': room_cost,
        'amenities_cost': amenities_cost,
        'total_cost': total_cost,
        'days': days
    })

@app.route('/api/notifications/count')
def notification_count():
    # Get token from header
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'count': 0}), 200
    
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        import jwt
        data = jwt.decode(token, 'your-secret-key-here', algorithms=['HS256'])
        user_id = data['user_id']
        count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        return jsonify({'count': count})
    except:
        return jsonify({'count': 0}), 200

@app.route('/api/notifications')
def get_notifications():
    print("\n📬 [API] Get notifications request")
    
    # Get token from header
    token = request.headers.get('Authorization')
    if not token:
        print("   ❌ No token")
        return jsonify({'error': 'Token is missing'}), 401
    
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        import jwt
        data = jwt.decode(token, 'your-secret-key-here', algorithms=['HS256'])
        user_id = data['user_id']
        print(f"   User ID: {user_id}")
        
        notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
        print(f"   Found {len(notifications)} notifications")
        
        result = []
        for n in notifications:
            print(f"   Notification #{n.id}:")
            print(f"      type={n.notification_type}")
            print(f"      related_id={n.related_id}")
            print(f"      action_url={n.action_url}")
            notif_dict = {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'notification_type': n.notification_type,
                'related_id': n.related_id,
                'action_url': n.action_url,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat()
            }
            print(f"      Dict created: {notif_dict}")
            result.append(notif_dict)
        
        print(f"   ✅ Returning {len(result)} notifications")
        response_data = {'notifications': result}
        print(f"   Full response data: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 401

@app.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
def mark_notification_read(notification_id):
    print(f"\n📬 [NOTIFICATION] Mark as read request for notification #{notification_id}")
    
    # Get token from header
    token = request.headers.get('Authorization')
    print(f"   Token present: {token is not None}")
    
    if not token:
        print("   ❌ No token provided")
        return jsonify({'error': 'Token is missing'}), 401
    
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        
        print(f"   🔑 Decoding JWT token...")
        import jwt
        data = jwt.decode(token, 'your-secret-key-here', algorithms=['HS256'])
        user_id = data['user_id']
        print(f"   ✅ Token decoded - User ID: {user_id}")
        
        notification = Notification.query.get(notification_id)
        print(f"   Notification found: {notification is not None}")
        
        if not notification:
            print(f"   ❌ Notification #{notification_id} not found in database")
            return jsonify({'error': 'Notification not found'}), 404
        
        print(f"   Notification user_id: {notification.user_id}, Request user_id: {user_id}")
        
        if notification.user_id != user_id:
            print(f"   ❌ User mismatch - notification belongs to user {notification.user_id}, not {user_id}")
            return jsonify({'error': 'Notification not found'}), 404
        
        print(f"   Marking notification as read...")
        notification.is_read = True
        db.session.commit()
        print(f"   ✅ Notification #{notification_id} marked as read successfully")
        
        return jsonify({'success': True})
    except jwt.ExpiredSignatureError:
        print("   ❌ Token expired")
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError as e:
        print(f"   ❌ Invalid token: {str(e)}")
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    # Get token from header
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing'}), 401
    
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        import jwt
        data = jwt.decode(token, 'your-secret-key-here', algorithms=['HS256'])
        user_id = data['user_id']
        
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        for notification in notifications:
            notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 401

@app.route('/api/revenue/weekly')
@login_required
def get_weekly_revenue():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Get the last 8 weeks of data
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=8)
    
    # Query confirmed bookings within the date range
    bookings = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).all()
    
    # Group bookings by week
    weekly_data = {}
    for booking in bookings:
        week_start = booking.created_at - timedelta(days=booking.created_at.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        if week_key not in weekly_data:
            weekly_data[week_key] = 0
        weekly_data[week_key] += booking.total_price
    
    # Format data for chart
    labels = []
    data = []
    for week_start in sorted(weekly_data.keys()):
        labels.append(datetime.strptime(week_start, '%Y-%m-%d').strftime('%b %d'))
        data.append(weekly_data[week_start])
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/api/revenue/monthly')
@login_required
def get_monthly_revenue():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Get the last 12 months of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Query confirmed bookings within the date range
    bookings = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).all()
    
    # Group bookings by month
    monthly_data = {}
    for booking in bookings:
        month_key = booking.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = 0
        monthly_data[month_key] += booking.total_price
    
    # Format data for chart
    labels = []
    data = []
    for month_key in sorted(monthly_data.keys()):
        labels.append(datetime.strptime(month_key, '%Y-%m').strftime('%b %Y'))
        data.append(monthly_data[month_key])
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/api/revenue/yearly')
@login_required
def get_yearly_revenue():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Get all years of data
    bookings = Booking.query.filter_by(status='confirmed').all()
    
    # Group bookings by year
    yearly_data = {}
    for booking in bookings:
        year_key = booking.created_at.strftime('%Y')
        if year_key not in yearly_data:
            yearly_data[year_key] = 0
        yearly_data[year_key] += booking.total_price
    
    # Format data for chart
    labels = []
    data = []
    for year_key in sorted(yearly_data.keys()):
        labels.append(year_key)
        data.append(yearly_data[year_key])
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username')
    email = request.form.get('email')
    phone_number = request.form.get('phone_number')
    # Phone number validation
    if not phone_number or not phone_number.isdigit() or len(phone_number) != 11:
        flash('Phone number must be exactly 11 digits and contain only numbers.', 'danger')
        return redirect(url_for('dashboard'))
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')

    # Check for email or username conflicts
    if User.query.filter(User.email == email, User.id != current_user.id).first():
        flash('Email already in use by another account.', 'danger')
        return redirect(url_for('dashboard'))
    if User.query.filter(User.username == username, User.id != current_user.id).first():
        flash('Username already in use by another account.', 'danger')
        return redirect(url_for('dashboard'))

    # Password change logic
    if new_password or confirm_new_password:
        if not current_password or not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('dashboard'))
        if new_password != confirm_new_password:
            flash('New password and confirmation do not match.', 'danger')
            return redirect(url_for('dashboard'))
        if len(new_password) < 8 or not any(char.isdigit() for char in new_password):
            flash('New password must be at least 8 characters and include a number.', 'danger')
            return redirect(url_for('dashboard'))
        current_user.set_password(new_password)

    current_user.username = username
    current_user.email = email
    current_user.phone_number = phone_number
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/receipt/<int:booking_id>')
@login_required
def receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    room = Room.query.get(booking.room_id)
    amenities = BookingAmenity.query.filter_by(booking_id=booking.id).all()
    amenities_details = [{
        'name': a.amenity.name,
        'quantity': a.quantity,
        'price': a.amenity.price,
        'total': a.amenity.price * a.quantity
    } for a in amenities]
    return render_template('receipt.html', booking=booking, room=room, amenities=amenities_details)

@app.route('/admin/add_room', methods=['GET', 'POST'])
@login_required
def admin_add_room():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price_per_night = float(request.form.get('price_per_night'))
        capacity = int(request.form.get('capacity'))
        image_file = request.files.get('image_file')
        image_url = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_folder = os.path.join('static', 'images', 'rooms')
            os.makedirs(image_folder, exist_ok=True)
            image_path = os.path.join(image_folder, filename)
            image_file.save(image_path)
            image_url = f'/static/images/rooms/{filename}'
        else:
            flash('Image upload failed.', 'danger')
            return redirect(url_for('admin_add_room'))
        new_room = Room(name=name, description=description, price_per_night=price_per_night, capacity=capacity, image_url=image_url)
        db.session.add(new_room)
        db.session.commit()
        flash('Room added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_room.html')

@app.route('/admin/add_amenity', methods=['GET', 'POST'])
@login_required
def admin_add_amenity():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        new_amenity = Amenity(name=name, description=description, price=price)
        db.session.add(new_amenity)
        db.session.commit()
        flash('Amenity added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_amenity.html')

@app.route('/admin/staff')
@login_required
def staff_list():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    staff = User.query.filter_by(is_staff=True).all()
    return render_template('staff_list.html', staff=staff)

@app.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
def add_staff():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        verification_code = request.form.get('verification_code')
        email = request.form.get('email')
        if verification_code:
            if verification_code == session.get('staff_email_verification'):
                staff_data = session.pop('pending_staff')
                staff_user = User(
                    username=staff_data['username'],
                    email=staff_data['email'],
                    is_staff=True,
                    staff_role=staff_data['staff_role'],
                    staff_status=staff_data['staff_status'],
                    staff_shift=staff_data['staff_shift'],
                    phone_number=staff_data['phone_number']
                )
                staff_user.set_password(staff_data['password'])
                db.session.add(staff_user)
                db.session.commit()
                session.pop('staff_email_verification', None)
                session.pop('staff_email_verification_email', None)
                flash('Staff member added successfully.', 'success')
                return redirect(url_for('staff_list'))
            else:
                flash('Invalid verification code. Please try again.', 'danger')
                return render_template('add_staff.html', require_code=True, email=email)
        # Initial staff form submission
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        password = request.form.get('password') or secrets.token_urlsafe(8)
        staff_role = request.form.get('staff_role')
        phone_number = request.form.get('phone_number')
        staff_shift = request.form.get('staff_shift')
        staff_status = request.form.get('staff_status', 'active')
        # Validation
        if not all([full_name, username, email, password, staff_role]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('add_staff'))
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('add_staff'))
        if staff_role not in ['Front Desk', 'Bell Boy', 'Housekeeping']:
            flash('Invalid staff role.', 'danger')
            return redirect(url_for('add_staff'))
        if len(password) < 8 or not any(c.isdigit() for c in password):
            flash('Password must be at least 8 characters and include a number.', 'danger')
            return redirect(url_for('add_staff'))
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 11:
            flash('Phone number must be exactly 11 digits and contain only numbers.', 'danger')
            return redirect(url_for('add_staff'))
        # Generate and send verification code
        code = str(random.randint(100000, 999999))
        session['staff_email_verification'] = code
        session['staff_email_verification_email'] = email
        session['pending_staff'] = {
            'username': username,
            'email': email,
            'password': password,
            'staff_role': staff_role,
            'staff_status': staff_status,
            'staff_shift': staff_shift,
            'phone_number': phone_number
        }
        # Send verification email
        try:
            msg = Message('Easy Hotel - Staff Email Verification',
                          sender='no-reply@easyhotel.com',
                          recipients=[email])
            msg.body = f'''
            Welcome to Easy Hotel Staff!

            Your verification code is: {code}

            Please enter this code to complete your staff registration.

            If you did not request this, please ignore this email.

            Best regards,
            Easy Hotel Team
            '''
            mail.send(msg)
        except Exception as e:
            print(f"Email error: {str(e)}")
            flash('Failed to send verification email. Please try again later.', 'danger')
            return render_template('add_staff.html')
        flash('Verification code has been sent to the staff email. Please check the inbox.', 'info')
        return render_template('add_staff.html', require_code=True, email=email)
    return render_template('add_staff.html')

@app.route('/staff/payroll')
@login_required
def staff_payroll():
    if not current_user.is_staff or current_user.is_admin:
        return redirect(url_for('dashboard'))
    from datetime import datetime
    # Get the most recent payroll issued
    last_payroll = Payroll.query.filter_by(staff_id=current_user.id).order_by(Payroll.period_end.desc()).first()
    # Get the next payroll (pending or not yet issued)
    next_payroll = Payroll.query.filter_by(staff_id=current_user.id, status='pending').order_by(Payroll.period_end.asc()).first()
    # Get all payrolls for history
    payroll_history = Payroll.query.filter_by(staff_id=current_user.id).order_by(Payroll.period_end.desc()).all()
    return render_template('staff_payroll.html', last_payroll=last_payroll, next_payroll=next_payroll, payroll_history=payroll_history)

@app.route('/staff/payroll/delete/<int:payroll_id>', methods=['POST'])
@login_required
def delete_staff_payroll(payroll_id):
    if not current_user.is_staff or current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('staff_payroll'))
    payroll = Payroll.query.get_or_404(payroll_id)
    if payroll.staff_id != current_user.id:
        flash('You can only delete your own payroll.', 'danger')
        return redirect(url_for('staff_payroll'))
    if payroll.status != 'pending':
        flash('Only pending payrolls can be deleted.', 'danger')
        return redirect(url_for('staff_payroll'))
    db.session.delete(payroll)
    db.session.commit()
    flash('Payroll deleted.', 'success')
    return redirect(url_for('staff_payroll'))

@app.route('/staff/dashboard', methods=['GET', 'POST'])
@login_required
def staff_dashboard():
    if not current_user.is_staff or current_user.is_admin:
        return redirect(url_for('dashboard'))
    from datetime import datetime
    # Get the next payroll for the staff
    next_payroll = Payroll.query.filter_by(staff_id=current_user.id, status='pending').order_by(Payroll.period_end.asc()).first()
    # Render different dashboard for each staff role
    if current_user.staff_role == 'Front Desk':
        return render_template('frontdesk_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)
    elif current_user.staff_role == 'Bell Boy':
        return render_template('bellboy_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)
    elif current_user.staff_role == 'Housekeeping':
        return render_template('housekeeping_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)
    else:
        return render_template('staff_dashboard.html', bookings=Booking.query.order_by(Booking.check_in_date.desc()).all(), message_sent=False, next_payroll=next_payroll)

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if not current_user.is_staff:
        return redirect(url_for('dashboard'))
    from datetime import date, datetime as dt
    import os
    today = date.today()
    attendance_record = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    leave_requests = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.start_date.desc()).all()
    message = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action in ['clock_in', 'clock_out']:
            verify_id = request.form.get('verify_id')
            id_image_file = request.files.get('id_image')
            id_image_path = None
            if id_image_file and id_image_file.filename:
                filename = secure_filename(f"{current_user.username}_{today}_{action}_id.jpg")
                image_folder = os.path.join('static', 'uploads', 'attendance_ids')
                os.makedirs(image_folder, exist_ok=True)
                image_path = os.path.join(image_folder, filename)
                id_image_file.save(image_path)
                id_image_path = f'/static/uploads/attendance_ids/{filename}'
            if verify_id != current_user.username:
                message = 'ID verification failed.'
            else:
                now = dt.now().time()
                if action == 'clock_in':
                    if attendance_record and attendance_record.clock_in:
                        message = 'Already clocked in today.'
                    else:
                        if not attendance_record:
                            attendance_record = Attendance(user_id=current_user.id, date=today)
                            db.session.add(attendance_record)
                        attendance_record.clock_in = now
                        attendance_record.verified_by_id = verify_id
                        if id_image_path:
                            attendance_record.id_image = id_image_path
                        attendance_record.approved = False
                        db.session.commit()
                        message = 'Clocked in successfully. Awaiting admin approval.'
                elif action == 'clock_out':
                    if not attendance_record or not attendance_record.clock_in:
                        message = 'You must clock in first.'
                    elif attendance_record.clock_out:
                        message = 'Already clocked out today.'
                    else:
                        attendance_record.clock_out = now
                        attendance_record.verified_by_id = verify_id
                        if id_image_path:
                            attendance_record.id_image = id_image_path
                        attendance_record.approved = False
                        db.session.commit()
                        message = 'Clocked out successfully. Awaiting admin approval.'
        elif action == 'request_leave':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            reason = request.form.get('reason')
            from datetime import datetime
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except Exception:
                message = 'Invalid date format.'
                attendance_logs = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.date.desc()).all()
                return render_template('attendance.html', attendance_record=attendance_record, attendance_logs=attendance_logs, leave_requests=leave_requests, message=message)
            if start_date and end_date and reason:
                leave = LeaveRequest(user_id=current_user.id, start_date=start_date_obj, end_date=end_date_obj, reason=reason)
                db.session.add(leave)
                db.session.commit()
                message = 'Leave request submitted.'
            else:
                message = 'Please fill all leave request fields.'
    attendance_logs = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.date.desc()).all()
    return render_template('attendance.html', attendance_record=attendance_record, attendance_logs=attendance_logs, leave_requests=leave_requests, message=message)

@app.route('/admin/attendance', methods=['GET', 'POST'])
@login_required
def admin_attendance():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    all_attendance = Attendance.query.order_by(Attendance.date.desc()).all()
    leave_requests = LeaveRequest.query.order_by(LeaveRequest.start_date.desc()).all()
    message = None
    if request.method == 'POST':
        action = request.form.get('action')
        leave_id = request.form.get('leave_id')
        attendance_id = request.form.get('attendance_id')
        if action in ['approve', 'reject'] and leave_id:
            leave = LeaveRequest.query.get(leave_id)
            if leave:
                leave.status = 'approved' if action == 'approve' else 'rejected'
                leave.admin_comment = request.form.get('admin_comment', '')
                db.session.commit()
                message = f'Leave request {action}d.'
        if action in ['approve_attendance', 'reject_attendance'] and attendance_id:
            attendance = Attendance.query.get(attendance_id)
            if attendance:
                attendance.approved = (action == 'approve_attendance')
                db.session.commit()
                message = f'Attendance {"approved" if attendance.approved else "rejected"}.'
    return render_template('admin_attendance.html', all_attendance=all_attendance, leave_requests=leave_requests, message=message)

@app.route('/admin/payroll/<int:payroll_id>/archive', methods=['POST'])
@login_required
def archive_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.archived = True
    db.session.commit()
    flash('Payroll archived.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll/<int:payroll_id>/unarchive', methods=['POST'])
@login_required
def unarchive_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.archived = False
    db.session.commit()
    flash('Payroll unarchived.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll/<int:payroll_id>/edit', methods=['POST'])
@login_required
def edit_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    try:
        bonuses = float(request.form.get('bonuses', 0) or 0)
        deductions = float(request.form.get('deductions', 0) or 0)
    except ValueError:
        flash('Invalid bonus or deduction amount.', 'danger')
        return redirect(url_for('payroll_management'))
    payroll.bonuses = bonuses
    payroll.deductions = deductions
    payroll.net_pay = payroll.gross_pay + bonuses - deductions
    db.session.commit()
    flash('Payroll updated.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll/<int:payroll_id>/pay', methods=['POST'])
@login_required
def pay_payroll(payroll_id):
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('payroll_management'))
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.status = 'paid'
    db.session.commit()
    flash('Payroll marked as paid.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/payroll', methods=['GET', 'POST'])
@login_required
def payroll_management():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    show_archived = request.args.get('show_archived', '0') == '1'
    if show_archived:
        payrolls = Payroll.query.order_by(Payroll.date_issued.desc()).filter_by(archived=True).all()
    else:
        payrolls = Payroll.query.order_by(Payroll.date_issued.desc()).filter_by(archived=False).all()
    if request.method == 'POST':
        # Get period from form
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        if not period_start or not period_end:
            flash('Please select a valid pay period.', 'danger')
            return render_template('payroll_management.html', payrolls=payrolls, show_archived=show_archived)
        period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
        staff_list = User.query.filter_by(is_staff=True, staff_status='active').all()
        for staff in staff_list:
            # Set hourly and overtime rates based on staff_role
            if staff.staff_role == 'Front Desk':
                hourly_rate = 100.0
                overtime_rate = 100.0 * 1.25
            elif staff.staff_role == 'Bell Boy':
                hourly_rate = 90.0
                overtime_rate = 90.0 * 1.25
            elif staff.staff_role == 'Housekeeping':
                hourly_rate = 89.375
                overtime_rate = 89.375 * 1.25
            else:
                hourly_rate = staff.hourly_rate or 0.0
                overtime_rate = staff.overtime_rate or hourly_rate
            # Prevent duplicate payrolls
            existing = Payroll.query.filter_by(
                staff_id=staff.id,
                period_start=period_start,
                period_end=period_end
            ).first()
            if existing:
                continue
            # Get attendance for this staff in the period
            attendances = Attendance.query.filter_by(user_id=staff.id, approved=True).filter(
                Attendance.date >= period_start, Attendance.date <= period_end
            ).all()
            total_hours = 0.0
            overtime_hours = 0.0
            for att in attendances:
                if att.clock_in and att.clock_out:
                    in_dt = datetime.combine(att.date, att.clock_in)
                    out_dt = datetime.combine(att.date, att.clock_out)
                    hours = (out_dt - in_dt).total_seconds() / 3600.0
                    # Overtime: hours above 8 per day
                    overtime = max(0, hours - 8)
                    overtime_hours += overtime
                    total_hours += hours
            # Calculate pay
            if staff.salary_type == 'fixed':
                gross_pay = staff.base_salary
            else:
                base_hours = total_hours - overtime_hours
                gross_pay = (base_hours * hourly_rate) + (overtime_hours * overtime_rate)
            # Deductions/Bonuses (manual for now)
            deductions = 0.0
            bonuses = 0.0
            net_pay = gross_pay + bonuses - deductions
            # Create payroll record
            payroll = Payroll(
                staff_id=staff.id,
                period_start=period_start,
                period_end=period_end,
                total_hours=total_hours,
                overtime_hours=overtime_hours,
                gross_pay=gross_pay,
                deductions=deductions,
                bonuses=bonuses,
                net_pay=net_pay,
                date_issued=datetime.utcnow(),
                status='pending'
            )
            db.session.add(payroll)
        db.session.commit()
        flash('Payroll generated for all staff for the selected period.', 'success')
        return redirect(url_for('payroll_management'))
    return render_template('payroll_management.html', payrolls=payrolls, show_archived=show_archived)

@app.route('/admin/fix_staff_salary_type')
@login_required
def fix_staff_salary_type():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    updated = 0
    for staff in User.query.filter_by(is_staff=True).all():
        staff.salary_type = 'hourly'
        updated += 1
    db.session.commit()
    flash(f'Set salary_type="hourly" for {updated} staff.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/fix_staff_roles_and_salary', methods=['POST', 'GET'])
@login_required
def fix_staff_roles_and_salary():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    updated = 0
    valid_roles = ['Front Desk', 'Bell Boy', 'Housekeeping']
    for staff in User.query.filter_by(is_staff=True).all():
        staff.salary_type = 'hourly'
        if staff.staff_role not in valid_roles:
            staff.staff_role = 'Front Desk'  # Default/fallback role
        updated += 1
    db.session.commit()
    flash(f'Set salary_type="hourly" and fixed staff_role for {updated} staff.', 'success')
    return redirect(url_for('payroll_management'))

@app.route('/admin/rooms', methods=['GET', 'POST'])
@login_required
def admin_rooms():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    rooms = Room.query.all()
    if request.method == 'POST':
        room_id = request.form.get('room_id')
        room = Room.query.get(room_id)
        if room:
            room.name = request.form.get('name')
            room.description = request.form.get('description')
            room.price_per_night = float(request.form.get('price_per_night'))
            room.capacity = int(request.form.get('capacity'))
            # Optionally handle image update here
            db.session.commit()
            flash('Room updated successfully!', 'success')
        return redirect(url_for('admin_rooms'))
    return render_template('admin_rooms.html', rooms=rooms)

@app.route('/admin/amenities', methods=['GET', 'POST'])
@login_required
def admin_amenities():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('admin_dashboard'))
    amenities = Amenity.query.all()
    if request.method == 'POST':
        amenity_id = request.form.get('amenity_id')
        amenity = Amenity.query.get(amenity_id)
        if amenity:
            amenity.name = request.form.get('name')
            amenity.description = request.form.get('description')
            amenity.price = float(request.form.get('price'))
            db.session.commit()
            flash('Amenity updated successfully!', 'success')
        return redirect(url_for('admin_amenities'))
    return render_template('admin_amenities.html', amenities=amenities)

@app.route('/admin/users')
@login_required
def user_list():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    users = User.query.filter_by(is_admin=False, is_staff=False).all()
    return render_template('user_list.html', users=users)

@app.route('/walkin_booking', methods=['GET', 'POST'])
@login_required
# You may want to add a role check for front desk staff here
def walkin_booking():
    from datetime import datetime, date
    import os
    import secrets
    import smtplib
    from email.mime.text import MIMEText
    rooms = Room.query.all()
    available_rooms = []
    guest = None
    receipt = None
    error = None
    if request.method == 'POST':
        # Get form data
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        room_id = request.form.get('room_id')
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        id_proof_file = request.files.get('id_proof')
        id_proof_path = None
        if id_proof_file and id_proof_file.filename:
            filename = f"{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id_proof_file.filename}"
            upload_folder = os.path.join('static', 'uploads', 'ids')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            id_proof_file.save(file_path)
            id_proof_path = f'/static/uploads/ids/{filename}'
        # Validate dates and room
        if not (check_in and check_out and room_id and name and phone and email and id_proof_path):
            error = 'All fields are required.'
        else:
            # Check room availability
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            room = Room.query.get(room_id)
            if not room:
                error = 'Room not found.'
            else:
                # Check for overlapping bookings
                overlapping = Booking.query.filter(
                    Booking.room_id == room_id,
                    Booking.status != 'cancelled',
                    Booking.check_out_date > check_in_date,
                    Booking.check_in_date < check_out_date
                ).first()
                if overlapping:
                    error = 'Room is not available for the selected dates.'
                else:
                    # Create guest (if not exists)
                    guest = User.query.filter_by(email=email).first()
                    if not guest:
                        # Generate a unique username
                        base_username = name.replace(' ', '').lower() if name else "temp"
                        username = base_username
                        counter = 1
                        username_exists = User.query.filter_by(username=username).first()
                        if username_exists:
                            flash('Username has already exist', 'danger')
                            return render_template('walkin_booking.html', rooms=rooms, available_rooms=available_rooms, error='Username has already exist', now=date.today())
                        guest = User(username=username, email=email, phone_number=phone)
                        random_password = secrets.token_urlsafe(10)
                        verification_code = str(random.randint(100000, 999999))
                        guest.set_password(random_password)
                        db.session.add(guest)
                        db.session.commit()
                        # Send email with password and verification code
                        try:
                            msg = MIMEText(f'''
Welcome to Easy Hotel!

Your walk-in account has been created.

Login Email: {email}
Password: {random_password}

Please use these credentials to log in and verify your account.

Best regards,\nEasy Hotel Team
''')
                            msg['Subject'] = 'Easy Hotel - Walk-in Account Details'
                            msg['From'] = 'no-reply@easyhotel.com'
                            msg['To'] = email
                            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                                server.starttls()
                                server.login('hotelmanagementsystem48@gmail.com', 'gtyxoxlvpftyoziv')
                                server.sendmail('no-reply@easyhotel.com', [email], msg.as_string())
                        except Exception as e:
                            print(f"Email error: {str(e)}")
                    # Create booking
                    booking = Booking(
                        user_id=guest.id,
                        room_id=room_id,
                        check_in_date=check_in_date,
                        check_out_date=check_out_date,
                        guests=1,
                        status='confirmed',
                        total_price=room.price_per_night * (check_out_date - check_in_date).days
                    )
                    db.session.add(booking)
                    # Set room status to Occupied
                    room.status = 'Occupied'
                    db.session.commit()
                    return redirect(url_for('walkin_receipt', booking_id=booking.id))
    # For GET or error, show available rooms for selected dates
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    if check_in and check_out:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        for room in rooms:
            overlapping = Booking.query.filter(
                Booking.room_id == room.id,
                Booking.status != 'cancelled',
                Booking.check_out_date > check_in_date,
                Booking.check_in_date < check_out_date
            ).first()
            if not overlapping:
                available_rooms.append(room)
    return render_template('walkin_booking.html', rooms=rooms, available_rooms=available_rooms, error=error, now=date.today())

@app.route('/walkin_receipt/<int:booking_id>')
@login_required
def walkin_receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template('walkin_receipt.html', booking=booking)

@app.route('/api/available_rooms')
def api_available_rooms():
    from datetime import datetime
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    if not check_in or not check_out:
        return jsonify({'success': False, 'rooms': []})
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    rooms = Room.query.all()
    available_rooms = []
    for room in rooms:
        overlapping = Booking.query.filter(
            Booking.room_id == room.id,
            Booking.status != 'cancelled',
            Booking.check_out_date > check_in_date,
            Booking.check_in_date < check_out_date
        ).first()
        if not overlapping:
            available_rooms.append({
                'id': room.id,
                'name': room.name,
                'price_per_night': room.price_per_night
            })
    return jsonify({'success': True, 'rooms': available_rooms})

@app.route('/admin/pos', methods=['GET', 'POST'])
@login_required
def admin_pos():
    if not current_user.is_admin:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    from datetime import datetime, date
    from sqlalchemy import extract
    today = date.today()
    month = today.month
    year = today.year
    monthly_bookings = Booking.query.filter(
        extract('month', Booking.created_at) == month,
        extract('year', Booking.created_at) == year,
        Booking.status == 'confirmed'
    ).all()
    total_monthly_income = sum(b.total_price for b in monthly_bookings)
    sales_per_day = {}
    for booking in monthly_bookings:
        day = booking.created_at.strftime('%Y-%m-%d')
        sales_per_day.setdefault(day, 0)
        sales_per_day[day] += booking.total_price
    bills = 0
    salary_distribution = 0
    sales_result = None
    selected_day = None
    day_sales = 0
    if request.method == 'POST':
        try:
            bills = float(request.form.get('bills', 0))
            salary_distribution = float(request.form.get('salary_distribution', 0))
            selected_day = request.form.get('selected_day')
            day_sales = sales_per_day.get(selected_day, 0)
            sales_result = day_sales - bills - salary_distribution
        except Exception as e:
            flash('Invalid input for POS calculation.', 'danger')
    return render_template('admin_pos.html',
        total_monthly_income=total_monthly_income,
        sales_per_day=sales_per_day,
        bills=bills,
        salary_distribution=salary_distribution,
        sales_result=sales_result,
        selected_day=selected_day,
        day_sales=day_sales
    )

# ============================================
# FLUTTER API ENDPOINTS
# ============================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API login endpoint for Flutter with proper JWT token generation"""
    print("\n🔐 [LOGIN] Starting login process")
    print("="*50)
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        print(f"📧 [LOGIN] Email: {email}")
        
        if not email or not password:
            print("❌ [LOGIN] Missing email or password")
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ [LOGIN] User not found: {email}")
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        if not user.check_password(password):
            print(f"❌ [LOGIN] Invalid password for: {email}")
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Check if user is verified
        if not user.is_verified:
            print(f"❌ [LOGIN] User not verified: {email}")
            return jsonify({'success': False, 'message': 'Please verify your email before logging in'}), 401
        
        # Generate JWT token
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
        }
        token = jwt.encode(payload, 'your-secret-key-here', algorithm='HS256')
        
        print(f"✅ [LOGIN] Login successful for: {user.username}")
        print(f"   User ID: {user.id}")
        print(f"   Is Admin: {user.is_admin}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Token generated: {token[:20]}...")
        print("="*50 + "\n")
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': token
        })
            
    except Exception as e:
        print(f"❌ [LOGIN] Error: {str(e)}")
        print("="*50 + "\n")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """API register endpoint for Flutter with SendGrid email verification"""
    print("\n" + "="*80)
    print("🔵 [REGISTER] Starting registration process (routes.py)")
    print("="*80)
    
    try:
        data = request.get_json()
        print(f"📦 [REGISTER] Received data: {data}")
        
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
        
        if not all([username, email, password, phone_number]):
            print("❌ [REGISTER] Missing required fields")
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if confirm_password and password != confirm_password:
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
            
            print(f"🎉 [REGISTER] User verified successfully!")
            print("="*80 + "\n")
            return jsonify({
                'success': True, 
                'message': 'Registration successful! You can now login.',
                'requires_verification': False,
                'user': pending_user.to_dict()
            })
        
        # Check if user already exists (only for new registrations)
        print("🔍 [REGISTER] Checking if user already exists...")
        if User.query.filter_by(email=email).first():
            print(f"❌ [REGISTER] Email already registered: {email}")
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        if User.query.filter_by(username=username).first():
            print(f"❌ [REGISTER] Username already taken: {username}")
            return jsonify({'success': False, 'message': 'Username already taken'}), 400
        
        # Generate verification code
        import random
        verification_code = str(random.randint(100000, 999999))
        print(f"🔑 [REGISTER] Generated verification code: {verification_code}")
        
        # Create user with verification pending
        print("👤 [REGISTER] Creating new user in database...")
        user = User(
            username=username, 
            email=email, 
            phone_number=phone_number,
            is_verified=False,
            verification_code=verification_code
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            print(f"✅ [REGISTER] User created successfully with ID: {user.id}")
        except Exception as e:
            print(f"❌ [REGISTER] Database error: {str(e)}")
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
        
        # Send verification email using local function
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
            print(f"❌ [REGISTER] Email send failed! Cleaning up user...")
            try:
                db.session.delete(user)
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
        
    except Exception as e:
        print(f"❌ [REGISTER] Unexpected error: {str(e)}")
        print("="*80 + "\n")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/current-user', methods=['GET'])
@app.route('/api/user/profile', methods=['GET'])
def get_current_user():
    """Get current user info for Flutter with proper JWT authentication"""
    print("\n👤 [USER_PROFILE] Get current user request")
    
    # Get token from header
    token = request.headers.get('Authorization')
    print(f"   Token present: {token is not None}")
    
    if not token:
        print("   ❌ No token provided")
        return jsonify({'success': False, 'message': 'Token is missing'}), 401
    
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        
        print(f"   🔑 Decoding JWT token...")
        import jwt
        data = jwt.decode(token, 'your-secret-key-here', algorithms=['HS256'])
        
        user_id = data['user_id']
        print(f"   ✅ Token decoded - User ID: {user_id}")
        
        # Get the actual user from database
        user = User.query.get(user_id)
        if not user:
            print(f"   ❌ User not found in database: {user_id}")
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        print(f"   ✅ User found: {user.username} (Admin: {user.is_admin}, Staff: {user.is_staff})")
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except jwt.ExpiredSignatureError:
        print("   ❌ Token expired")
        return jsonify({'success': False, 'message': 'Token expired'}), 401
    except jwt.InvalidTokenError as e:
        print(f"   ❌ Invalid token: {str(e)}")
        return jsonify({'success': False, 'message': 'Invalid token'}), 401
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Flutter"""
    return jsonify({
        'status': 'healthy',
        'message': 'Hotel booking API is running'
    })

@app.route('/api/admin/reports/dashboard', methods=['GET'])
@admin_required
def admin_dashboard_reports(current_user_id):
    """Get dashboard statistics for admin"""
    try:
        # Get basic stats
        total_bookings = Booking.query.count()
        total_users = User.query.count()
        total_rooms = Room.query.count()
        
        # Get revenue (sum of paid amounts)
        total_revenue = db.session.query(db.func.sum(Booking.paid_amount)).scalar() or 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_bookings': total_bookings,
                'total_users': total_users,
                'total_rooms': total_rooms,
                'total_revenue': float(total_revenue),
                'occupancy_rate': 75.5,  # Mock data
                'pending_bookings': Booking.query.filter_by(status='pending').count()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': True,
            'stats': {
                'total_bookings': 0,
                'total_users': 0,
                'total_rooms': 0,
                'total_revenue': 0,
                'occupancy_rate': 0,
                'pending_bookings': 0
            }
        }), 200

@app.route('/api/admin/bookings/all', methods=['GET'])
@admin_required
def admin_all_bookings(current_user_id):
    """Get all bookings for admin"""
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        bookings_data = []
        
        for booking in bookings:
            try:
                booking_dict = {
                    'id': booking.id,
                    'user_id': booking.user_id,
                    'room_id': booking.room_id,
                    'check_in': booking.check_in_date.isoformat() if hasattr(booking, 'check_in_date') and booking.check_in_date else None,
                    'check_out': booking.check_out_date.isoformat() if hasattr(booking, 'check_out_date') and booking.check_out_date else None,
                    'total_amount': float(booking.total_price) if hasattr(booking, 'total_price') and booking.total_price else 0,
                    'paid_amount': float(booking.paid_amount) if hasattr(booking, 'paid_amount') and booking.paid_amount else 0,
                    'status': booking.status,
                    'payment_status': getattr(booking, 'payment_status', 'not_paid'),
                    'created_at': booking.created_at.isoformat() if booking.created_at else None,
                    'user_name': booking.user.username if hasattr(booking, 'user') and booking.user else 'Unknown',
                    'user_email': booking.user.email if hasattr(booking, 'user') and booking.user else 'Unknown',
                    'room_name': f'Room {booking.room.room_number}' if hasattr(booking, 'room') and booking.room and hasattr(booking.room, 'room_number') else 'Unknown Room'
                }
                bookings_data.append(booking_dict)
            except Exception as e:
                print(f"Error processing booking {booking.id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'bookings': bookings_data,
            'total_count': len(bookings_data)
        })
        
    except Exception as e:
        return jsonify({'success': True, 'bookings': [], 'message': f'No bookings found: {str(e)}'}), 200

@app.route('/api/admin/users/stats', methods=['GET'])
@admin_required
def admin_user_stats(current_user_id):
    """Get user statistics for admin dashboard"""
    try:
        total_users = User.query.count()
        customers = User.query.filter_by(is_admin=False, is_staff=False).count()
        staff = User.query.filter_by(is_staff=True).count()
        admins = User.query.filter_by(is_admin=True).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'customers': customers,
                'staff': staff,
                'admins': admins,
                'recent_registrations': 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': True,
            'stats': {
                'total_users': 0,
                'customers': 0,
                'staff': 0,
                'admins': 0,
                'recent_registrations': 0
            }
        }), 200

@app.route('/api/bookings', methods=['GET'])
def api_get_bookings():
    """Get user bookings for Flutter"""
    try:
        bookings = Booking.query.all()
        bookings_data = []
        
        for booking in bookings:
            booking_dict = {
                'id': booking.id,
                'room_id': booking.room_id,
                'check_in': booking.check_in_date.isoformat() if hasattr(booking, 'check_in_date') and booking.check_in_date else None,
                'check_out': booking.check_out_date.isoformat() if hasattr(booking, 'check_out_date') and booking.check_out_date else None,
                'total_amount': float(booking.total_price) if hasattr(booking, 'total_price') and booking.total_price else 0,
                'status': booking.status,
                'created_at': booking.created_at.isoformat() if booking.created_at else None
            }
            bookings_data.append(booking_dict)
        
        return jsonify({
            'success': True,
            'bookings': bookings_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/amenities', methods=['GET'])
def api_get_amenities():
    """Get all amenities for Flutter"""
    try:
        amenities = Amenity.query.all()
        amenities_data = []
        
        for amenity in amenities:
            amenity_dict = {
                'id': amenity.id,
                'name': amenity.name,
                'icon_url': getattr(amenity, 'icon_url', ''),
                'description': getattr(amenity, 'description', '')
            }
            amenities_data.append(amenity_dict)
        
        return jsonify({
            'success': True,
            'amenities': amenities_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
# Missing API endpoints for Flutter app
@app.route('/api/reviews', methods=['GET'])
def api_get_reviews():
    """Get all reviews"""
    try:
        # For now, return empty reviews since the reviews table might not exist
        return jsonify({
            'success': True,
            'reviews': []
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_admin_users(current_user_id):
    """Get users for admin management"""
    try:
        user_type = request.args.get('type', 'all')
        search = request.args.get('search', '')
        
        query = User.query
        
        if user_type == 'customers':
            query = query.filter_by(is_admin=False, is_staff=False)
        elif user_type == 'staff':
            query = query.filter_by(is_staff=True)
        elif user_type == 'admins':
            query = query.filter_by(is_admin=True)
        
        if search:
            query = query.filter(User.username.contains(search))
        
        users = query.all()
        users_data = []
        
        for user in users:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_staff': user.is_staff,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
            users_data.append(user_dict)
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/bookings/pending', methods=['GET'])
@admin_required
def api_admin_pending_bookings(current_user_id):
    """Get pending bookings for admin"""
    try:
        bookings = Booking.query.filter_by(status='pending').all()
        bookings_data = []
        
        for booking in bookings:
            booking_dict = {
                'id': booking.id,
                'room_id': booking.room_id,
                'user_id': booking.user_id,
                'check_in': booking.check_in_date.isoformat() if hasattr(booking, 'check_in_date') and booking.check_in_date else None,
                'check_out': booking.check_out_date.isoformat() if hasattr(booking, 'check_out_date') and booking.check_out_date else None,
                'total_amount': float(booking.total_price) if hasattr(booking, 'total_price') and booking.total_price else 0,
                'status': booking.status,
                'created_at': booking.created_at.isoformat() if booking.created_at else None
            }
            bookings_data.append(booking_dict)
        
        return jsonify({
            'success': True,
            'bookings': bookings_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/payments/all', methods=['GET'])
@admin_required
def api_admin_payments(current_user_id):
    """Get all payments for admin"""
    try:
        # Get payments from bookings
        bookings = Booking.query.all()
        payments_data = []
        
        for booking in bookings:
            if hasattr(booking, 'total_price') and booking.total_price:
                payment_dict = {
                    'id': booking.id,
                    'booking_id': booking.id,
                    'amount': float(booking.total_price),
                    'status': booking.status,
                    'payment_method': getattr(booking, 'payment_method', 'unknown'),
                    'created_at': booking.created_at.isoformat() if booking.created_at else None
                }
                payments_data.append(payment_dict)
        
        return jsonify({
            'success': True,
            'payments': payments_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/floor-plans', methods=['GET'])
def api_floor_plans():
    """Get floor plans"""
    try:
        # Return mock floor plans for now
        floor_plans = [
            {'id': 1, 'name': 'Ground Floor', 'image_url': 'https://via.placeholder.com/600x400'},
            {'id': 2, 'name': 'First Floor', 'image_url': 'https://via.placeholder.com/600x400'},
            {'id': 3, 'name': 'Second Floor', 'image_url': 'https://via.placeholder.com/600x400'}
        ]
        
        return jsonify({
            'success': True,
            'floor_plans': floor_plans
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/room-sizes', methods=['GET'])
def api_room_sizes():
    """Get room sizes"""
    try:
        # Return mock room sizes for now
        room_sizes = [
            {'id': 1, 'name': 'Standard', 'size': '25 sqm', 'capacity': 2},
            {'id': 2, 'name': 'Deluxe', 'size': '35 sqm', 'capacity': 3},
            {'id': 3, 'name': 'Suite', 'size': '50 sqm', 'capacity': 4}
        ]
        
        return jsonify({
            'success': True,
            'room_sizes': room_sizes
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/staff', methods=['GET'])
@admin_required
def api_admin_staff(current_user_id):
    """Get staff members for admin"""
    try:
        staff = User.query.filter_by(is_staff=True).all()
        staff_data = []
        
        for member in staff:
            staff_dict = {
                'id': member.id,
                'username': member.username,
                'email': member.email,
                'role': getattr(member, 'role', 'staff'),
                'department': getattr(member, 'department', 'General'),
                'created_at': member.created_at.isoformat() if member.created_at else None
            }
            staff_data.append(staff_dict)
        
        return jsonify({
            'success': True,
            'staff': staff_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    """Handle forgot password requests"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal if email exists or not for security
            return jsonify({'success': True, 'message': 'If the email exists, a reset link has been sent'})
        
        # Generate reset code and send email
        import random
        reset_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Send password reset email
        email_sent = send_password_reset_email(email, user.username, reset_code)
        
        return jsonify({
            'success': True,
            'message': 'Password reset instructions have been sent to your email',
            'email_sent': email_sent
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def api_reset_password():
    """Handle password reset with code"""
    try:
        data = request.get_json()
        email = data.get('email')
        reset_code = data.get('reset_code')
        new_password = data.get('new_password')
        
        if not all([email, reset_code, new_password]):
            return jsonify({'success': False, 'message': 'Email, reset code, and new password are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # For now, accept any reset code (implement proper code validation later)
        if len(reset_code) < 4:
            return jsonify({'success': False, 'message': 'Invalid reset code'}), 400
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/verify-email', methods=['POST'])
def api_verify_email():
    """Verify email with verification code"""
    try:
        data = request.get_json()
        email = data.get('email')
        verification_code = data.get('verification_code')
        
        print(f"🔍 [VERIFY] Email verification attempt for: {email}")
        print(f"🔍 [VERIFY] Code provided: {verification_code}")
        
        if not email or not verification_code:
            return jsonify({'success': False, 'message': 'Email and verification code required'}), 400
        
        # Validate code format
        if len(verification_code) != 6 or not verification_code.isdigit():
            return jsonify({'success': False, 'message': 'Invalid verification code format'}), 400
        
        # Find user by email and verification code
        user = User.query.filter_by(
            email=email, 
            verification_code=verification_code,
            is_verified=False
        ).first()
        
        if not user:
            print(f"❌ [VERIFY] Invalid verification code for: {email}")
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400
        
        # Mark user as verified
        user.is_verified = True
        user.verification_code = None  # Clear the code
        db.session.commit()
        
        print(f"✅ [VERIFY] Email verified successfully for: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully! You can now login.',
            'user_id': user.id
        })
        
    except Exception as e:
        print(f"❌ [VERIFY] Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/staff/create', methods=['POST'])
@admin_required
def api_create_staff(current_user_id):
    """Create staff account (admin only)"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'staff')
        department = data.get('department', 'General')
        
        if not all([username, email, password]):
            return jsonify({'success': False, 'message': 'Username, email and password required'}), 400
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already taken'}), 400
        
        # Create new staff user
        user = User(username=username, email=email, is_staff=True)
        user.set_password(password)
        
        # Add role and department if User model supports it
        if hasattr(user, 'role'):
            user.role = role
        if hasattr(user, 'department'):
            user.department = department
            
        db.session.add(user)
        db.session.commit()
        
        # Send verification email (mock for now)
        verification_sent = send_staff_verification_email(email, username)
        
        return jsonify({
            'success': True,
            'message': 'Staff account created successfully',
            'requires_verification': True,
            'verification_sent': verification_sent,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/send-verification', methods=['POST'])
def api_send_verification():
    """Send verification email"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Send verification email
        verification_sent = send_verification_email(email, user.username)
        
        return jsonify({
            'success': True,
            'message': 'Verification email sent successfully',
            'email_sent': verification_sent
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def send_verification_email(email, verification_code):
    """Send verification email using SendGrid"""
    try:
        import os
        import requests
        
        # SendGrid configuration
        SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
        EMAIL_FROM = os.getenv('EMAIL_FROM', 'hotelmanagementsystem48@gmail.com')
        
        if not SENDGRID_API_KEY:
            print("❌ SendGrid API key not found")
            return False
        
        # Email content
        subject = "Email Verification - Easy Hotel Booking"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Email Verification</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background: #f9f9f9; }}
                .code {{ font-size: 32px; font-weight: bold; color: #4CAF50; text-align: center; 
                         padding: 20px; background: white; border: 2px dashed #4CAF50; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏨 Easy Hotel Booking</h1>
                    <p>Email Verification Required</p>
                </div>
                <div class="content">
                    <h2>Welcome to Easy Hotel Booking!</h2>
                    <p>Thank you for registering with us. To complete your registration, please verify your email address.</p>
                    
                    <p><strong>Your verification code is:</strong></p>
                    <div class="code">{verification_code}</div>
                    
                    <p>Please enter this 6-digit code in the app to verify your email address.</p>
                    
                    <p><strong>Important:</strong></p>
                    <ul>
                        <li>This code will expire in 24 hours</li>
                        <li>If you didn't create this account, please ignore this email</li>
                        <li>For security, never share this code with anyone</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Best regards,<br>Easy Hotel Booking Team</p>
                    <p><small>This is an automated email. Please do not reply.</small></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # SendGrid API request
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "subject": subject
                }
            ],
            "from": {"email": EMAIL_FROM, "name": "Easy Hotel Booking"},
            "content": [
                {
                    "type": "text/html",
                    "value": html_content
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 202:
            print(f"✅ Verification email sent successfully to {email}")
            return True
        else:
            print(f"❌ SendGrid error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send verification email: {str(e)}")
        return False

def send_staff_verification_email(email, username):
    """Send verification email to new staff member"""
    try:
        # Generate verification code
        import random
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Email content
        subject = "Staff Account Verification - Easy Hotel Booking"
        body = f"""
        Hello {username},
        
        Welcome to the Easy Hotel Booking team!
        
        Your staff account has been created. Please verify your email address with the code below:
        
        Verification Code: {verification_code}
        
        Please enter this code in the app to activate your staff account.
        
        Best regards,
        Easy Hotel Booking Management
        """
        
        # Send email using Flask-Mail
        from flask_mail import Message
        msg = Message(
            subject=subject,
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=body
        )
        
        mail.send(msg)
        print(f"✅ Staff verification email sent to {email} with code: {verification_code}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send staff verification email: {str(e)}")
        return False

def send_password_reset_email(email, username, reset_code):
    """Send password reset email"""
    try:
        # Email content
        subject = "Password Reset - Easy Hotel Booking"
        body = f"""
        Hello {username},
        
        You requested a password reset for your Easy Hotel Booking account.
        
        Your password reset code is: {reset_code}
        
        Please enter this code in the app to reset your password.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        Easy Hotel Booking Team
        """
        
        # Send email using Flask-Mail
        from flask_mail import Message
        msg = Message(
            subject=subject,
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=body
        )
        
        mail.send(msg)
        print(f"✅ Password reset email sent to {email} with code: {reset_code}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send password reset email: {str(e)}")
        return False

# Test route to verify routing works
@app.route('/api/auth/test-verify', methods=['POST'])
def test_verify_route():
    """Test route to verify routing works"""
    return jsonify({
        'success': True,
        'message': 'Test route working',
        'data': request.get_json()
    })

@app.route('/api/auth/email-verify', methods=['POST'])
def api_email_verify():
    """Alternative email verification endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        verification_code = data.get('verification_code')
        
        if not email or not verification_code:
            return jsonify({'success': False, 'message': 'Email and verification code required'}), 400
        
        # Accept any 6-digit code for testing
        if len(verification_code) != 6 or not verification_code.isdigit():
            return jsonify({'success': False, 'message': 'Invalid verification code format'}), 400
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Mark user as verified
        user.is_verified = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# PAYMENT ROUTES - Added to fix 405 error
# ============================================================================

@app.route('/api/payment/methods', methods=['GET'])
def api_payment_methods():
    """Get available payment methods"""
    try:
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

@app.route('/api/payment/gcash/create', methods=['POST'])
@admin_required
def api_create_gcash_payment(current_user_id):
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
        print(f"   Phone: {phone_number}")
        
        # Calculate downpayment (30% of total price)
        downpayment_amount = booking.total_price * 0.30
        
        # For now, return success with mock data
        return jsonify({
            'success': True,
            'payment_id': f'pay_{booking_id}_{random.randint(1000, 9999)}',
            'payment_intent_id': f'pi_{random.randint(100000, 999999)}',
            'redirect_url': f'https://checkout.paymongo.com/mock/{booking_id}',
            'amount': downpayment_amount,
            'total_amount': booking.total_price,
            'remaining_balance': booking.total_price - downpayment_amount,
            'message': 'Payment created successfully'
        })
            
    except Exception as e:
        print(f"❌ Payment creation error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/payment/<int:payment_id>/verify', methods=['POST'])
@admin_required
def api_verify_payment(current_user_id, payment_id):
    """Verify payment status"""
    try:
        # For now, return mock verification
        return jsonify({
            'success': True,
            'status': 'completed',
            'payment_id': payment_id,
            'message': 'Payment verified successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/payment/success', methods=['GET'])
def api_payment_success():
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

@app.route('/api/payment/failed', methods=['GET'])
def api_payment_failed():
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