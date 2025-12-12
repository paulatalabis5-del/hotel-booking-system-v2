import os
import logging
import pytz

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, login_manager
from models import User, Room, Amenity, Booking, BookingAmenity, Rating, Notification
from flask_migrate import Migrate

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__, 
            template_folder='EasyHotelBooking/templates',
            static_folder='EasyHotelBooking/static')
app.secret_key = os.environ.get("SESSION_SECRET", "easy_hotel_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Enable CORS for Flutter web and mobile
CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:*",
    "http://127.0.0.1:*",
    "http://192.168.100.159:*",
    "http://localhost:54391",
    "http://127.0.0.1:54391",
    "http://192.168.100.159:54391"
]}}, supports_credentials=True)

# Use SQLite for now (PostgreSQL has Python 3.13 compatibility issues on Render)
print("📁 Using SQLite database for deployment")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hotel.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

with app.app_context():
    # Import the models here so their tables will be created
    import models  # noqa: F401
    db.create_all()  # Create new tables
    
    # Import routes after models to avoid circular imports
    from routes import *  # noqa: F401, F403
    
    # Register API routes blueprint
    try:
        from api_routes import api_bp
        if 'unique_api_blueprint_xyz789' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(api_bp)
            print("✅ API Blueprint registered successfully")
    except Exception as e:
        print(f"❌ Error registering API blueprint: {str(e)}")
        pass  # Continue without API blueprint
    
    # Register attendance routes (optional)
    try:
        from attendance_routes import attendance_bp
        if 'attendance' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(attendance_bp)
            print("✅ Attendance routes registered")
    except (ImportError, ValueError):
        print("⚠️ Attendance routes not available (optional)")
        pass  # Module not found or blueprint already registered
    
    # Register refund routes (optional)
    try:
        from refund_routes import refund_bp
        if 'refund' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(refund_bp)
            print("✅ Refund routes registered")
    except (ImportError, ValueError):
        print("⚠️ Refund routes not available (optional)")
        pass  # Module not found or blueprint already registered
    
    # Register front desk routes (optional)
    try:
        from front_desk_routes import front_desk_bp
        if 'front_desk' not in [bp.name for bp in app.blueprints.values()]:
            app.register_blueprint(front_desk_bp)
            print("✅ Front desk routes registered")
    except (ImportError, ValueError):
        print("⚠️ Front desk routes not available (optional)")
        pass  # Module not found or blueprint already registered
    
    # Create initial data
    from init_data import create_initial_data
    create_initial_data()

# Add Jinja filter for Philippine time
@app.template_filter('to_ph_time')
def to_ph_time(dt):
    if not dt:
        return dt
    utc = pytz.utc
    ph_tz = pytz.timezone('Asia/Manila')
    if dt.tzinfo is None:
        dt = utc.localize(dt)
    return dt.astimezone(ph_tz)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
