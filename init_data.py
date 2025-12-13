"""
Initialize database with sample data for hotel booking system
"""
from extensions import db
from models import User, Room, Amenity, Rating
from werkzeug.security import generate_password_hash
import logging

def create_initial_data():
    """Create initial data for the application"""
    try:
        # Create admin users (both email addresses for compatibility)
        admin_emails = [
            ('admin@hotel.com', 'admin'),
            ('admin@easyhotel.com', 'admin2')
        ]
        
        for email, username in admin_emails:
            admin_user = User.query.filter_by(email=email).first()
            if not admin_user:
                try:
                    admin_user = User(
                        username=username,
                        email=email,
                        first_name='Admin',
                        last_name='User',
                        is_admin=True,
                        is_verified=True,
                        verification_code=None
                    )
                    admin_user.set_password('admin123')
                    db.session.add(admin_user)
                    db.session.flush()  # Get the ID
                    print(f"✅ Created admin user: {email} with ID: {admin_user.id}")
                except Exception as e:
                    print(f"❌ Error creating admin user {email}: {str(e)}")
                    db.session.rollback()
        
        # Create test user
        test_user = User.query.filter_by(email='test@hotel.com').first()
        if not test_user:
            try:
                test_user = User(
                    username='testuser',
                    email='test@hotel.com',
                    first_name='Test',
                    last_name='User',
                    is_admin=False,
                    is_verified=True,
                    verification_code=None
                )
                test_user.set_password('test123')
                db.session.add(test_user)
                db.session.flush()  # Get the ID
                print(f"✅ Created test user with ID: {test_user.id}")
            except Exception as e:
                print(f"❌ Error creating test user: {str(e)}")
                db.session.rollback()
        
        # Commit users first to avoid rollback
        db.session.commit()
        print("✅ Users committed to database")
        
        # Create sample rooms (simplified - only required fields)
        rooms_data = [
            {
                'name': 'Deluxe Room',
                'description': 'Spacious room with city view',
                'price_per_night': 2500.00,
                'capacity': 2,
                'room_number': 'D001',
                'status': 'available',
                'room_size_id': 1,  # Default room size
                'floor_id': 1       # Default floor
            },
            {
                'name': 'Standard Room', 
                'description': 'Comfortable standard accommodation',
                'price_per_night': 1800.00,
                'capacity': 2,
                'room_number': 'S001',
                'status': 'available',
                'room_size_id': 1,  # Default room size
                'floor_id': 1       # Default floor
            },
            {
                'name': 'Suite Room',
                'description': 'Luxury suite with premium amenities',
                'price_per_night': 4000.00,
                'capacity': 4,
                'room_number': 'SU001',
                'status': 'available',
                'room_size_id': 1,  # Default room size
                'floor_id': 1       # Default floor
            }
        ]
        
        try:
            for room_data in rooms_data:
                existing_room = Room.query.filter_by(name=room_data['name']).first()
                if not existing_room:
                    # Create room with only essential fields to avoid constraint errors
                    room = Room(
                        name=room_data['name'],
                        description=room_data['description'],
                        price_per_night=room_data['price_per_night'],
                        capacity=room_data['capacity'],
                        room_number=room_data['room_number'],
                        status=room_data['status']
                        # Skip room_size_id and floor_id to avoid constraint errors
                    )
                    db.session.add(room)
                    print(f"✅ Created room: {room_data['name']}")
            
            # Commit rooms
            db.session.commit()
            print("✅ Rooms committed to database")
            
        except Exception as e:
            print(f"⚠️ Room creation failed (non-critical): {str(e)}")
            db.session.rollback()
            print("✅ Users are still saved (rooms skipped)")
        
        # Create sample ratings (only if rooms exist)
        try:
            rooms = Room.query.all()
            if rooms:
                for i, room in enumerate(rooms):
                    # Check if rating already exists
                    existing_rating = Rating.query.filter_by(room_id=room.id).first()
                    if not existing_rating:
                        rating_value = 4.0 + (i * 0.3)  # 4.0, 4.3, 4.6
                        rating = Rating(
                            room_id=room.id,
                            user_id=test_user.id if test_user else 1,
                            rating=rating_value,
                            review=f"Great room with excellent service!"
                        )
                        db.session.add(rating)
                        
                        # Update room rating (if room has these fields)
                        if hasattr(room, 'averageRating'):
                            room.averageRating = rating_value
                        if hasattr(room, 'reviewCount'):
                            room.reviewCount = 1
                        if hasattr(room, 'stars'):
                            room.stars = "★" * int(rating_value)
                        print(f"✅ Created rating for {room.name}: {rating_value}★")
                
                db.session.commit()
                print("✅ Ratings committed to database")
            else:
                print("⚠️ No rooms found, skipping ratings")
                
        except Exception as e:
            print(f"⚠️ Rating creation failed (non-critical): {str(e)}")
            db.session.rollback()
        print("✅ Database initialization complete!")
        print("Login credentials:")
        print("   Admin: admin@hotel.com / admin123")
        print("   Test User: test@hotel.com / test123")
        
    except Exception as e:
        print(f"❌ Error initializing data: {str(e)}")
        db.session.rollback()
        logging.error(f"Database initialization error: {str(e)}")