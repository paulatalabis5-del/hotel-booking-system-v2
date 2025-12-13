"""
Simplified API routes without email verification requirement
This allows users to register without email verification
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import jwt
import os
from datetime import datetime, timedelta
from models import User, Room, Rating
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

# Create API blueprint
api_bp = Blueprint('simple_api_no_email', __name__, url_prefix='/api')

# JWT Secret Key
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register new user without email verification"""
    try:
        data = request.get_json()
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        phone_number = data.get('phone_number')
        
        print(f"[REGISTER] Attempting registration for: {email}")
        
        # Basic validation
        if not all([username, email, password]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check if user exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                print(f"[REGISTER] Username already taken: {username}")
                return jsonify({'success': False, 'message': 'Username already taken'}), 400
            else:
                print(f"[REGISTER] Email already registered: {email}")
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Create new user (no email verification required)
        new_user = User(
            username=username,
            email=email,
            phone_number=phone_number,
            is_verified=True  # Skip email verification
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"[REGISTER] User created successfully: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now login.',
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
        
        print(f"[LOGIN] Attempting login for: {email}")
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            print(f"[LOGIN] Invalid credentials for: {email}")
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token_payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        
        token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        print(f"[LOGIN] Login successful for: {email}")
        
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
            
            # Create star display (using text instead of emoji)
            stars_text = ""
            if avg_rating > 0:
                full_stars = int(avg_rating)
                stars_text = "★" * full_stars
            
            room_data = {
                'id': room.id,
                'name': room.name,
                'description': room.description,
                'price_per_night': room.price_per_night,
                'capacity': room.capacity,
                'averageRating': round(avg_rating, 1),
                'reviewCount': len(ratings),
                'stars': stars_text,
                'image_url': getattr(room, 'image_url', ''),
                'room_type': getattr(room, 'room_type', 'Standard')
            }
            room_list.append(room_data)
        
        return jsonify({'data': room_list}), 200
        
    except Exception as e:
        print(f"[ROOMS] Error: {str(e)}")
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
            
            # Create star display (using text instead of emoji)
            stars_text = ""
            if avg_rating > 0:
                full_stars = int(avg_rating)
                stars_text = "★" * full_stars
            
            ratings_data.append({
                'room_id': room.id,
                'room_name': room.name,
                'average_rating': round(avg_rating, 1),
                'review_count': len(ratings),
                'stars': stars_text
            })
        
        return jsonify({'ratings': ratings_data}), 200
        
    except Exception as e:
        print(f"[RATINGS] Error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get ratings: {str(e)}'}), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is working',
        'timestamp': datetime.utcnow().isoformat()
    }), 200