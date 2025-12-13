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
        
        # First, create required dependencies for rooms
        try:
            # Create default room size if it doesn't exist
            from models import RoomSize, FloorPlan
            
            default_room_size = RoomSize.query.first()
            if not default_room_size:
                default_room_size = RoomSize(
                    room_type_name='Standard',
                    features='Basic room amenities',
                    max_adults=2,
                    max_children=1
                )
                db.session.add(default_room_size)
                db.session.flush()
                print(f"✅ Created default room size with ID: {default_room_size.id}")
            
            # Create default floor plan if it doesn't exist
            default_floor = FloorPlan.query.first()
            if not default_floor:
                default_floor = FloorPlan(
                    floor_name='Ground Floor',
                    room_size_id=default_room_size.id,
                    number_of_rooms=10,
                    start_room_number='101'
                )
                db.session.add(default_floor)
                db.session.flush()
                print(f"✅ Created default floor plan with ID: {default_floor.id}")
            
            db.session.commit()
            print("✅ Room dependencies committed")
            
        except Exception as e:
            print(f"⚠️ Could not create room dependencies: {str(e)}")
            db.session.rollback()
        
        # Now create sample rooms with proper foreign keys
        try:
            # Get the default IDs
            default_room_size = RoomSize.query.first()
            default_floor = FloorPlan.query.first()
            
            if default_room_size and default_floor:
                rooms_data = [
                    {
                        'name': 'Deluxe Room',
                        'description': 'Spacious room with city view',
                        'price_per_night': 2500.00,
                        'capacity': 2,
                        'room_number': 'D001',
                        'status': 'available',
                        'room_size_id': default_room_size.id,
                        'floor_id': default_floor.id
                    },
                    {
                        'name': 'Standard Room', 
                        'description': 'Comfortable standard accommodation',
                        'price_per_night': 1800.00,
                        'capacity': 2,
                        'room_number': 'S001',
                        'status': 'available',
                        'room_size_id': default_room_size.id,
                        'floor_id': default_floor.id
                    },
                    {
                        'name': 'Suite Room',
                        'description': 'Luxury suite with premium amenities',
                        'price_per_night': 4000.00,
                        'capacity': 4,
                        'room_number': 'SU001',
                        'status': 'available',
                        'room_size_id': default_room_size.id,
                        'floor_id': default_floor.id
                    }
                ]
                
                for room_data in rooms_data:
                    existing_room = Room.query.filter_by(name=room_data['name']).first()
                    if not existing_room:
                        room = Room(**room_data)
                        db.session.add(room)
                        print(f"✅ Created room: {room_data['name']}")
                
                db.session.commit()
                print("✅ Rooms committed to database")
            else:
                print("⚠️ Could not create rooms - missing dependencies")
                
        except Exception as e:
            print(f"⚠️ Room creation failed: {str(e)}")
            db.session.rollback()
            print("✅ Users are still saved (rooms skipped)")
        
        # Create sample amenities
        try:
            from models import Amenity
            
            amenities_data = [
                {'name': 'WiFi', 'description': 'Free high-speed internet', 'price': 0.0},
                {'name': 'Air Conditioning', 'description': 'Climate control', 'price': 0.0},
                {'name': 'Room Service', 'description': '24/7 room service', 'price': 500.0},
                {'name': 'Breakfast', 'description': 'Continental breakfast', 'price': 300.0},
                {'name': 'Spa Access', 'description': 'Access to spa facilities', 'price': 800.0}
            ]
            
            for amenity_data in amenities_data:
                existing_amenity = Amenity.query.filter_by(name=amenity_data['name']).first()
                if not existing_amenity:
                    amenity = Amenity(**amenity_data)
                    db.session.add(amenity)
                    print(f"✅ Created amenity: {amenity_data['name']}")
            
            db.session.commit()
            print("✅ Amenities committed to database")
            
        except Exception as e:
            print(f"⚠️ Amenity creation failed (non-critical): {str(e)}")
            db.session.rollback()
        
        # Skip ratings for now (requires bookings first)
        print("⚠️ Skipping ratings creation (requires bookings)")
        print("✅ Database initialization complete!")
        print("Login credentials:")
        print("   Admin: admin@hotel.com / admin123")
        print("   Test User: test@hotel.com / test123")
        
    except Exception as e:
        print(f"❌ Error initializing data: {str(e)}")
        db.session.rollback()
        logging.error(f"Database initialization error: {str(e)}")