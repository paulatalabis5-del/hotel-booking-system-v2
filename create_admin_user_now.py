"""
Create admin user immediately - for fixing missing admin account
"""

from extensions import db
from models import User
from werkzeug.security import generate_password_hash

def create_admin_users():
    """Create admin users with both email addresses"""
    
    print("🔧 CREATING ADMIN USERS")
    print("=" * 40)
    
    # Admin accounts to create
    admin_accounts = [
        {
            'username': 'admin',
            'email': 'admin@hotel.com',
            'password': 'admin123'
        },
        {
            'username': 'admin2', 
            'email': 'admin@easyhotel.com',
            'password': 'admin123'
        }
    ]
    
    for account in admin_accounts:
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=account['email']).first()
            
            if existing_user:
                print(f"✅ Admin user already exists: {account['email']}")
                # Make sure they're admin and verified
                existing_user.is_admin = True
                existing_user.is_verified = True
                existing_user.verification_code = None
                db.session.commit()
                print(f"   Updated admin status for: {account['email']}")
            else:
                # Create new admin user
                admin_user = User(
                    username=account['username'],
                    email=account['email'],
                    first_name='Admin',
                    last_name='User',
                    is_admin=True,
                    is_verified=True,
                    verification_code=None
                )
                admin_user.set_password(account['password'])
                
                db.session.add(admin_user)
                db.session.commit()
                
                print(f"✅ Created new admin user: {account['email']}")
                print(f"   Username: {account['username']}")
                print(f"   Password: {account['password']}")
                
        except Exception as e:
            print(f"❌ Error with {account['email']}: {str(e)}")
            db.session.rollback()
    
    print("\n📋 ADMIN LOGIN CREDENTIALS:")
    print("=" * 40)
    print("Option 1:")
    print("   Email: admin@hotel.com")
    print("   Password: admin123")
    print()
    print("Option 2:")
    print("   Email: admin@easyhotel.com") 
    print("   Password: admin123")
    print()
    print("✅ Both admin accounts are now available!")

if __name__ == "__main__":
    # This would need to be run in Flask app context
    print("This script creates admin users for the hotel booking system")
    print("Run this after deployment to ensure admin access")
    create_admin_users()