#!/usr/bin/env python3
"""
Initialize Database for Render Deployment
Run this once after deployment to set up tables and sample data
"""

import sys
sys.path.append('.')

def init_database():
    """Initialize database with tables and sample data"""
    
    print("Initializing database...")
    
    try:
        from app import app, db
        from models import User, Room, Booking, Rating
        from werkzeug.security import generate_password_hash
        from datetime import datetime, timedelta
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("Database tables created")
            
            # Create admin user
            admin = User.query.filter_by(email='admin@hotel.com').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@hotel.com',
                    password_hash=generate_password_hash('admin123'),
                    role='admin',
                    first_name='Hotel',
                    last_name='Administrator'
                )
                db.session.add(admin)
                print("Created admin user")
            
            # Create test user
            test_user = User.query.filter_by(email='test@hotel.com').first()
            if not test_user:
                test_user = User(
                    username='testuser',
                    email='test@hotel.com',
                    password_hash=generate_password_hash('test123'),
                    role='customer',
                    first_name='Test',
                    last_name='User'
                )
                db.session.add(test_user)
                print("Created test user")
            
            db.session.commit()
            
            # Create sample rooms
            if Room.query.count() == 0:
                rooms = [
                    {
                        'name': 'Deluxe Room',
                        'room_number': '101',
                        'description': 'Spacious deluxe room with city view',
                        'price_per_night': 150.0,
                        'capacity': 2,
                        'status': 'available'
                    },
                    {
                        'name': 'Standard Room',
                        'room_number': '102',
                        'description': 'Comfortable standard room',
                        'price_per_night': 100.0,
                        'capacity': 2,
                        'status': 'available'
                    },
                    {
                        'name': 'Suite Room',
                        'room_number': '201',
                        'description': 'Luxury suite with premium amenities',
                        'price_per_night': 250.0,
                        'capacity': 4,
                        'status': 'available'
                    }
                ]
                
                for room_data in rooms:
                    room = Room(**room_data)
                    db.session.add(room)
                
                db.session.commit()
                print("Created sample rooms")
            
            # Create sample bookings and ratings
            if Rating.query.count() == 0:
                rooms = Room.query.all()
                users = User.query.filter_by(role='customer').all()
                
                if rooms and users:
                    # Create sample booking
                    booking = Booking(
                        user_id=users[0].id,
                        room_id=rooms[0].id,
                        check_in_date=datetime.now().date() - timedelta(days=7),
                        check_out_date=datetime.now().date() - timedelta(days=5),
                        total_amount=300.0,
                        status='completed'
                    )
                    db.session.add(booking)
                    db.session.commit()
                    
                    # Create sample ratings
                    sample_ratings = [
                        {
                            'user_id': users[0].id,
                            'booking_id': booking.id,
                            'overall_rating': 5,
                            'room_rating': 5,
                            'amenities_rating': 4,
                            'service_rating': 5,
                            'comment': 'Excellent room! Very clean and comfortable.'
                        },
                        {
                            'user_id': users[0].id,
                            'booking_id': booking.id,
                            'overall_rating': 4,
                            'room_rating': 4,
                            'amenities_rating': 4,
                            'service_rating': 4,
                            'comment': 'Good room with nice amenities.'
                        }
                    ]
                    
                    for rating_data in sample_ratings:
                        rating = Rating(**rating_data)
                        db.session.add(rating)
                    
                    db.session.commit()
                    print("Created sample ratings")
            
            print("Database initialization complete!")
            print("Login credentials:")
            print("   Admin: admin@hotel.com / admin123")
            print("   Test User: test@hotel.com / test123")
            
    except Exception as e:
        print(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    init_database()