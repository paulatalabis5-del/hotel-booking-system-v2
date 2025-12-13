"""
Temporary fix to disable email verification for easier testing
This allows users to register without email verification
"""

import os
import sys

def create_no_verification_api_routes():
    """Create a simplified API routes file without email verification"""
    
    api_routes_content = '''
# Simplified API routes without email verification requirement
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import jwt
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
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now login.',
            'user_id': new_user.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token_payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        
        token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
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
            
            room_data = {
                'id': room.id,
                'name': room.name,
                'description': room.description,
                'price_per_night': room.price_per_night,
                'capacity': room.capacity,
                'averageRating': round(avg_rating, 1),
                'reviewCount': len(ratings),
                'stars': '⭐' * int(avg_rating) if avg_rating > 0 else '',
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
                'stars': '⭐' * int(avg_rating) if avg_rating > 0 else ''
            })
        
        return jsonify({'ratings': ratings_data}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to get ratings: {str(e)}'}), 500
'''
    
    return api_routes_content

def apply_no_verification_fix():
    """Apply the no email verification fix"""
    
    print("🔧 APPLYING NO EMAIL VERIFICATION FIX")
    print("=" * 50)
    
    # Create backup of original api_routes.py
    try:
        with open('api_routes.py', 'r') as f:
            original_content = f.read()
        
        with open('api_routes_backup.py', 'w') as f:
            f.write(original_content)
        
        print("✅ Backed up original api_routes.py")
    except Exception as e:
        print(f"⚠️ Could not backup original file: {e}")
    
    # Create simplified API routes
    simplified_content = create_no_verification_api_routes()
    
    try:
        with open('api_routes_simple.py', 'w') as f:
            f.write(simplified_content)
        
        print("✅ Created simplified API routes (api_routes_simple.py)")
    except Exception as e:
        print(f"❌ Failed to create simplified routes: {e}")
        return False
    
    print("\n📋 WHAT THIS FIX DOES:")
    print("✅ Removes email verification requirement")
    print("✅ Allows immediate user registration")
    print("✅ Provides basic login/register functionality")
    print("✅ Maintains room ratings API")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Replace api_routes.py with api_routes_simple.py")
    print("2. Commit and push changes")
    print("3. Redeploy on Render")
    print("4. Test registration with new email")
    
    return True

if __name__ == "__main__":
    apply_no_verification_fix()