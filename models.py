from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=False)  # New: staff flag
    staff_role = db.Column(db.String(50))  # New: staff role (Front Desk, Manager, etc.)
    staff_status = db.Column(db.String(20), default='active')  # New: active/inactive
    staff_shift = db.Column(db.String(50))  # New: shift timing (optional)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone_number = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=True)  # Email verification status
    verification_code = db.Column(db.String(10))  # Email verification code
    
    # Personal Information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    home_address = db.Column(db.Text)
    id_document_url = db.Column(db.String(500))  # Optional ID upload for verification
    
    # Relationships
    bookings = db.relationship('Booking', foreign_keys='Booking.user_id', backref='user', lazy='dynamic')
    bookings_checked_in = db.relationship('Booking', foreign_keys='Booking.checked_in_by', backref='staff_checked_in', lazy='dynamic')
    bookings_checked_out = db.relationship('Booking', foreign_keys='Booking.checked_out_by', backref='staff_checked_out', lazy='dynamic')
    ratings = db.relationship('Rating', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
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
            'first_name': self.first_name,
            'last_name': self.last_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
    def __repr__(self):
        return f'<User {self.username}>'

# ============================================
# NEW HOTEL MANAGEMENT MODELS
# ============================================

# 1. Amenities Master List
class AmenityMaster(db.Model):
    """Master list of all available amenities"""
    __tablename__ = 'amenity_master'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    amenity_details = db.relationship('AmenityDetail', backref='amenity', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AmenityMaster {self.name}>'

# 2. Room Sizes (Room Types)
class RoomSize(db.Model):
    """Room types with specifications"""
    __tablename__ = 'room_size'
    
    id = db.Column(db.Integer, primary_key=True)
    room_type_name = db.Column(db.String(50), nullable=False, unique=True)
    features = db.Column(db.Text)
    max_adults = db.Column(db.Integer, nullable=False)
    max_children = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    amenity_details = db.relationship('AmenityDetail', backref='room_size', lazy='dynamic', cascade='all, delete-orphan')
    rooms = db.relationship('Room', backref='room_size', lazy='dynamic')
    floor_plans = db.relationship('FloorPlan', backref='room_size', lazy='dynamic')
    
    def __repr__(self):
        return f'<RoomSize {self.room_type_name}>'

# 3. Amenity Details (Amenity-RoomType Mapping)
class AmenityDetail(db.Model):
    """Links amenities to specific room types"""
    __tablename__ = 'amenity_detail'
    
    id = db.Column(db.Integer, primary_key=True)
    amenity_id = db.Column(db.Integer, db.ForeignKey('amenity_master.id', ondelete='CASCADE'), nullable=False)
    room_size_id = db.Column(db.Integer, db.ForeignKey('room_size.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate mappings
    __table_args__ = (db.UniqueConstraint('amenity_id', 'room_size_id', name='_amenity_roomsize_uc'),)
    
    def __repr__(self):
        return f'<AmenityDetail {self.id}>'

# 4. Floor Plans
class FloorPlan(db.Model):
    """Hotel floors with auto-generated room numbers"""
    __tablename__ = 'floor_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    floor_name = db.Column(db.String(50), nullable=False)
    room_size_id = db.Column(db.Integer, db.ForeignKey('room_size.id'), nullable=False)
    number_of_rooms = db.Column(db.Integer, nullable=False)
    start_room_number = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rooms = db.relationship('Room', backref='floor', lazy='dynamic')
    
    def generate_room_numbers(self):
        """Generate list of room numbers based on start number and count"""
        try:
            start_num = int(self.start_room_number)
            return [str(start_num + i) for i in range(self.number_of_rooms)]
        except ValueError:
            # If start_room_number is not numeric, return empty list
            return []
    
    def __repr__(self):
        return f'<FloorPlan {self.floor_name}>'

# Association table for Room-Amenity many-to-many relationship
room_amenity = db.Table('room_amenity',
    db.Column('room_id', db.Integer, db.ForeignKey('room.id'), primary_key=True),
    db.Column('amenity_id', db.Integer, db.ForeignKey('amenity.id'), primary_key=True)
)

# 5. Rooms (Updated)
class Room(db.Model):
    """Individual room records with all details"""
    __tablename__ = 'room'
    
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), nullable=False, unique=True)
    room_size_id = db.Column(db.Integer, db.ForeignKey('room_size.id'), nullable=False)
    floor_id = db.Column(db.Integer, db.ForeignKey('floor_plan.id'), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    
    # 5 images for carousel
    image_1 = db.Column(db.String(255))
    image_2 = db.Column(db.String(255))
    image_3 = db.Column(db.String(255))
    image_4 = db.Column(db.String(255))
    image_5 = db.Column(db.String(255))
    
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Legacy fields for backward compatibility
    name = db.Column(db.String(100))  # Can be auto-generated from room_type + room_number
    description = db.Column(db.Text)  # Can be auto-generated from room_size features
    capacity = db.Column(db.Integer)  # Inherited from room_size (max_adults + max_children)
    image_url = db.Column(db.String(255))  # Kept for backward compatibility, use image_1
    
    # Relationships
    bookings = db.relationship('Booking', backref='room', lazy='dynamic')
    amenities = db.relationship('Amenity', secondary=room_amenity, backref=db.backref('rooms', lazy='dynamic'))
    
    @property
    def max_adults(self):
        """Inherited from room_size"""
        return self.room_size.max_adults if self.room_size else 0
    
    @property
    def max_children(self):
        """Inherited from room_size"""
        return self.room_size.max_children if self.room_size else 0
    
    @property
    def total_capacity(self):
        """Total capacity (adults + children)"""
        return self.max_adults + self.max_children
    
    @property
    def images(self):
        """Get list of all room images"""
        return [img for img in [self.image_1, self.image_2, self.image_3, self.image_4, self.image_5] if img]
    
    def __repr__(self):
        return f'<Room {self.room_number}>'

# Keep old Amenity model for backward compatibility with bookings
class Amenity(db.Model):
    """Legacy amenity model for booking add-ons"""
    __tablename__ = 'amenity'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    
    # Relationships
    booking_amenities = db.relationship('BookingAmenity', backref='amenity', lazy='dynamic')
    
    def __repr__(self):
        return f'<Amenity {self.name}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    
    # Booking dates
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    
    # Guest information
    num_adults = db.Column(db.Integer, nullable=False, default=1)
    num_children = db.Column(db.Integer, nullable=False, default=0)
    guests = db.Column(db.Integer, nullable=False)  # Total guests (for backward compatibility)
    guest_name = db.Column(db.String(100))
    guest_email = db.Column(db.String(120))
    guest_phone = db.Column(db.String(20))
    special_requests = db.Column(db.Text)
    
    # Pricing
    total_price = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)  # Amount paid by customer
    
    # Downpayment fields (30% of total)
    downpayment_amount = db.Column(db.Float, default=0.0)  # 30% of total_price
    downpayment_paid = db.Column(db.Boolean, default=False)  # True if downpayment is paid
    remaining_balance = db.Column(db.Float, default=0.0)  # Amount remaining to be paid
    payment_type = db.Column(db.String(50), default='full_payment')  # 'downpayment', 'full_payment', 'cash_on_arrival'
    
    # Booking status: pending, confirmed, checked_in, checked_out, cancelled, no_show
    status = db.Column(db.String(20), default="pending")
    
    # Check-in/Check-out tracking
    actual_check_in = db.Column(db.DateTime)
    actual_check_out = db.Column(db.DateTime)
    checked_in_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Staff who checked in
    checked_out_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Staff who checked out
    
    # Cancellation tracking
    cancellation_reason = db.Column(db.Text)
    cancelled_by = db.Column(db.String(20))  # 'user' or 'admin'
    cancelled_at = db.Column(db.DateTime)
    
    # Payment tracking
    # Payment status: not_paid, partially_paid, fully_paid, refunded, partially_refunded
    payment_status = db.Column(db.String(20), default="not_paid")
    payment_method = db.Column(db.String(50))  # cash, gcash, card, etc.
    
    # Refund tracking
    refund_status = db.Column(db.String(20))  # completed, pending, etc.
    refund_amount = db.Column(db.Float, default=0.0)  # Amount refunded to customer
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    booking_amenities = db.relationship('BookingAmenity', backref='booking', lazy='dynamic')
    
    @property
    def nights(self):
        """Calculate number of nights"""
        return (self.check_out_date - self.check_in_date).days
    
    @property
    def due_amount(self):
        """Calculate remaining amount to be paid"""
        return max(0, self.total_price - (self.paid_amount or 0))
    
    @property
    def is_active(self):
        """Check if booking is currently active (checked in)"""
        return self.status == 'checked_in'
    
    @property
    def can_check_in(self):
        """Check if booking can be checked in"""
        return self.status == 'confirmed' and self.check_in_date <= datetime.utcnow().date()
    
    @property
    def can_check_out(self):
        """Check if booking can be checked out"""
        return self.status == 'checked_in'
    
    def update_payment_status(self):
        """Automatically update payment status based on paid amount"""
        if self.paid_amount >= self.total_price:
            self.payment_status = 'fully_paid'
        elif self.paid_amount > 0:
            self.payment_status = 'partially_paid'
        else:
            self.payment_status = 'not_paid'
    
    def get_refund_eligibility(self):
        """
        Check if booking is eligible for refund based on cancellation policy.
        Policy: Free cancellation up to 24 hours before check-in.
        
        Returns:
            dict: Refund eligibility information
        """
        from datetime import timedelta
        
        if self.status == 'cancelled':
            return {
                'eligible': False,
                'reason': 'Booking already cancelled',
                'refund_amount': 0.0,
                'refund_percentage': 0
            }
        
        now = datetime.utcnow()
        check_in_datetime = datetime.combine(self.check_in_date, datetime.min.time())
        time_until_checkin = check_in_datetime - now
        hours_until_checkin = time_until_checkin.total_seconds() / 3600
        
        # Free cancellation if more than 24 hours before check-in
        is_refundable = hours_until_checkin > 24
        refund_amount = 0.0
        refund_percentage = 0
        
        if is_refundable and self.paid_amount:
            refund_amount = self.paid_amount
            refund_percentage = 100
        
        cancellation_deadline = check_in_datetime - timedelta(hours=24)
        
        return {
            'eligible': is_refundable,
            'refund_amount': refund_amount,
            'refund_percentage': refund_percentage,
            'hours_until_checkin': round(hours_until_checkin, 2),
            'cancellation_deadline': cancellation_deadline,
            'reason': 'Within free cancellation period' if is_refundable else 'Past cancellation deadline'
        }
    
    @property
    def is_refundable(self):
        """Quick check if booking is refundable"""
        return self.get_refund_eligibility()['eligible']
    
    @property
    def hours_until_checkin(self):
        """Calculate hours until check-in"""
        now = datetime.utcnow()
        check_in_datetime = datetime.combine(self.check_in_date, datetime.min.time())
        time_until_checkin = check_in_datetime - now
        return time_until_checkin.total_seconds() / 3600
    
    def to_dict(self):
        """Convert booking to dictionary for API responses"""
        room = Room.query.get(self.room_id)
        user = User.query.get(self.user_id)
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'guests': self.guests,
            'num_adults': self.num_adults,
            'num_children': self.num_children,
            'guest_name': self.guest_name,
            'guest_email': self.guest_email,
            'guest_phone': self.guest_phone,
            'special_requests': self.special_requests,
            'total_price': float(self.total_price) if self.total_price else 0.0,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0.0,
            'downpayment_amount': float(self.downpayment_amount) if self.downpayment_amount else 0.0,
            'downpayment_paid': self.downpayment_paid,
            'remaining_balance': float(self.remaining_balance) if self.remaining_balance else 0.0,
            'payment_type': self.payment_type,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'cancellation_reason': self.cancellation_reason,
            'cancelled_by': self.cancelled_by,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'actual_check_in': self.actual_check_in.isoformat() if self.actual_check_in else None,
            'actual_check_out': self.actual_check_out.isoformat() if self.actual_check_out else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'room': {
                'id': room.id,
                'name': room.name,
                'room_number': room.room_number,
                'price_per_night': float(room.price_per_night) if room.price_per_night else 0.0,
            } if room else None,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            } if user else None,
        }
    
    def __repr__(self):
        return f'<Booking {self.id}>'

class BookingAmenity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    amenity_id = db.Column(db.Integer, db.ForeignKey('amenity.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    def __repr__(self):
        return f'<BookingAmenity {self.id}>'

class Rating(db.Model):
    __tablename__ = 'rating'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    overall_rating = db.Column(db.Integer, nullable=False)  # Overall hotel experience
    room_rating = db.Column(db.Integer, nullable=False)     # Room quality and comfort
    amenities_rating = db.Column(db.Integer, nullable=False) # Quality of amenities
    service_rating = db.Column(db.Integer, nullable=False)   # Staff service quality
    comment = db.Column(db.Text)
    admin_reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('rating', uselist=False))
    
    def __repr__(self):
        return f'<Rating {self.id} by User {self.user_id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # 'booking', 'payment', 'refund', 'review', etc.
    related_id = db.Column(db.Integer)  # ID of related booking, payment, etc.
    action_url = db.Column(db.String(500))  # URL to navigate to when clicked
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        # Ensure all fields are included in the response
        print(f"      [to_dict FIXED VERSION] Called for Notification #{self.id}")
        print(f"         notification_type={self.notification_type}")
        print(f"         related_id={self.related_id}")
        print(f"         action_url={self.action_url}")
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'related_id': self.related_id,
            'action_url': self.action_url,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }
        print(f"      [to_dict FIXED VERSION] Returning: {result}")
        return result
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # Clock in/out with timestamps
    clock_in_time = db.Column(db.DateTime)
    clock_out_time = db.Column(db.DateTime)
    
    # Location tracking (GPS coordinates)
    clock_in_latitude = db.Column(db.Float)
    clock_in_longitude = db.Column(db.Float)
    clock_out_latitude = db.Column(db.Float)
    clock_out_longitude = db.Column(db.Float)
    
    # Location validation
    clock_in_location_valid = db.Column(db.Boolean, default=False)
    clock_out_location_valid = db.Column(db.Boolean, default=False)
    
    # ID verification
    verified_by_id = db.Column(db.String(64))  # Staff ID or admin ID
    id_image = db.Column(db.String(255))  # Path to uploaded ID image
    
    # Status tracking
    status = db.Column(db.String(20), default='clocked_in')  # clocked_in, clocked_out, absent
    notes = db.Column(db.Text)
    
    # Admin approval
    approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='attendance_records')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_attendances')
    
    @property
    def hours_worked(self):
        """Calculate hours worked"""
        if self.clock_in_time and self.clock_out_time:
            delta = self.clock_out_time - self.clock_in_time
            return round(delta.total_seconds() / 3600, 2)
        return 0.0
    
    def __repr__(self):
        return f'<Attendance {self.id} - User {self.user_id} - {self.date}>'

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_comment = db.Column(db.Text)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    shift = db.Column(db.String(20), nullable=False)  # Morning, Afternoon, Night, Custom
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    staff = db.relationship('User', foreign_keys=[staff_id], backref='schedules')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_schedules')
    
    def __repr__(self):
        return f'<Schedule {self.id} - Staff {self.staff_id} - {self.date}>'

class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    total_hours = db.Column(db.Float)
    overtime_hours = db.Column(db.Float)
    gross_pay = db.Column(db.Float)
    deductions = db.Column(db.Float)
    bonuses = db.Column(db.Float)
    net_pay = db.Column(db.Float)
    date_issued = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    staff = db.relationship('User', backref='payrolls')
    archived = db.Column(db.Boolean, default=False)

class PayrollBonus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll.id'))
    description = db.Column(db.String(128))
    amount = db.Column(db.Float)
    payroll = db.relationship('Payroll', backref='bonuses_list')

class PayrollDeduction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll.id'))
    description = db.Column(db.String(128))
    amount = db.Column(db.Float)
    payroll = db.relationship('Payroll', backref='deductions_list')

# Add payroll fields to User
User.salary_type = db.Column(db.String(20), default='fixed')  # 'fixed' or 'hourly'
User.base_salary = db.Column(db.Float, default=0.0)
User.hourly_rate = db.Column(db.Float, default=0.0)
User.overtime_rate = db.Column(db.Float, default=0.0)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # 'gcash', 'cash', 'card'
    payment_status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    
    # GCash specific fields
    gcash_reference_number = db.Column(db.String(100))
    gcash_transaction_id = db.Column(db.String(100))
    gcash_phone_number = db.Column(db.String(20))
    
    # Payment gateway fields
    gateway_response = db.Column(db.Text)  # Store full response from payment gateway
    gateway_transaction_id = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('payments', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('payments', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Payment {self.id} - {self.payment_method} - {self.amount}>'

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 'GCash', 'PayMaya', 'Cash', 'Card'
    code = db.Column(db.String(20), nullable=False)  # 'gcash', 'paymaya', 'cash', 'card'
    is_active = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)  # True for online payments
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(255))
    
    # Configuration for online payment methods
    api_key = db.Column(db.String(255))
    secret_key = db.Column(db.String(255))
    merchant_id = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<PaymentMethod {self.name}>'

# RFID Card Management
class RFIDCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_uid = db.Column(db.String(50), unique=True, nullable=False)  # RFID unique identifier
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_type = db.Column(db.String(20), nullable=False)  # 'staff_badge', 'room_key', 'access_card'
    is_active = db.Column(db.Boolean, default=True)
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    last_used = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Relationships
    user = db.relationship('User', backref='rfid_cards')
    
    def __repr__(self):
        return f'<RFIDCard {self.card_uid} - {self.card_type}>'

# RFID Access Log
class RFIDAccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rfid_card_id = db.Column(db.Integer, db.ForeignKey('rfid_card.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_type = db.Column(db.String(30), nullable=False)  # 'attendance', 'room_access', 'checkpoint'
    access_location = db.Column(db.String(100))  # 'front_desk', 'room_101', 'checkpoint_a'
    access_time = db.Column(db.DateTime, default=datetime.utcnow)
    access_granted = db.Column(db.Boolean, default=True)
    denial_reason = db.Column(db.String(100))  # If access denied
    
    # Relationships
    rfid_card = db.relationship('RFIDCard', backref='access_logs')
    user = db.relationship('User', backref='rfid_access_logs')
    
    def __repr__(self):
        return f'<RFIDAccessLog {self.id} - {self.access_type}>'

# Role-Based Feature Models

# 1. Front Desk Operations
class CheckInOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(20), nullable=False)  # 'check_in' or 'check_out'
    action_time = db.Column(db.DateTime, default=datetime.utcnow)
    guest_signature = db.Column(db.String(255))  # Path to signature image
    notes = db.Column(db.Text)
    room_condition = db.Column(db.String(50))  # 'excellent', 'good', 'needs_attention'
    
    # Relationships
    booking = db.relationship('Booking', backref='checkin_checkout_records')
    staff = db.relationship('User', backref='checkin_checkout_actions')

# 2. Housekeeping Management
class RoomStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False)  # 'clean', 'dirty', 'maintenance', 'out_of_order'
    last_cleaned = db.Column(db.DateTime)
    cleaned_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    inspection_status = db.Column(db.String(20), default='pending')  # 'pending', 'passed', 'failed'
    inspected_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    inspection_time = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='status_records')
    cleaner = db.relationship('User', foreign_keys=[cleaned_by], backref='cleaned_rooms')
    inspector = db.relationship('User', foreign_keys=[inspected_by], backref='inspected_rooms')

class CleaningTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # 'daily_cleaning', 'deep_cleaning', 'maintenance_cleaning'
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'completed', 'cancelled'
    scheduled_time = db.Column(db.DateTime, nullable=False)
    started_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer)  # in minutes
    actual_duration = db.Column(db.Integer)  # in minutes
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='cleaning_tasks')
    staff = db.relationship('User', backref='assigned_cleaning_tasks')

# 3. Security System
class SecurityPatrol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guard_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patrol_route = db.Column(db.String(100), nullable=False)  # 'lobby', 'floors_1_3', 'parking', 'perimeter'
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='in_progress')  # 'in_progress', 'completed', 'interrupted'
    checkpoints_visited = db.Column(db.Text)  # JSON array of checkpoint IDs
    observations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    guard = db.relationship('User', backref='security_patrols')

class SecurityIncident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)  # 'theft', 'disturbance', 'medical', 'fire', 'other'
    severity = db.Column(db.String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text)
    status = db.Column(db.String(20), default='open')  # 'open', 'investigating', 'resolved', 'closed'
    incident_time = db.Column(db.DateTime, nullable=False)
    resolved_time = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reporter = db.relationship('User', foreign_keys=[reported_by], backref='reported_incidents')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_incidents')

# 4. Maintenance Module
class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    location = db.Column(db.String(100))  # For non-room locations
    category = db.Column(db.String(50), nullable=False)  # 'plumbing', 'electrical', 'hvac', 'general'
    priority = db.Column(db.String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'
    status = db.Column(db.String(20), default='open')  # 'open', 'assigned', 'in_progress', 'completed', 'cancelled'
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float)
    scheduled_date = db.Column(db.DateTime)
    started_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room = db.relationship('Room', backref='work_orders')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='requested_work_orders')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_work_orders')

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'hvac', 'elevator', 'generator', 'security', 'kitchen'
    location = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    last_maintenance = db.Column(db.DateTime)
    next_maintenance = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='operational')  # 'operational', 'maintenance', 'broken', 'retired'
    maintenance_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EquipmentMaintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False)  # 'routine', 'repair', 'inspection', 'replacement'
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    maintenance_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float)
    parts_used = db.Column(db.Text)  # JSON array of parts
    next_maintenance_due = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    equipment = db.relationship('Equipment', backref='maintenance_records')
    technician = db.relationship('User', backref='equipment_maintenance_performed')

# 5. Manager Dashboard - Additional Analytics Models
class DailyReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.Date, nullable=False)
    total_revenue = db.Column(db.Float, default=0.0)
    occupancy_rate = db.Column(db.Float, default=0.0)
    new_bookings = db.Column(db.Integer, default=0)
    cancelled_bookings = db.Column(db.Integer, default=0)
    checkins = db.Column(db.Integer, default=0)
    checkouts = db.Column(db.Integer, default=0)
    maintenance_requests = db.Column(db.Integer, default=0)
    security_incidents = db.Column(db.Integer, default=0)
    staff_attendance = db.Column(db.Float, default=0.0)  # percentage
    guest_satisfaction = db.Column(db.Float, default=0.0)  # average rating
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StaffPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    evaluation_date = db.Column(db.Date, nullable=False)
    performance_score = db.Column(db.Float)  # 1-10 scale
    punctuality_score = db.Column(db.Float)  # 1-10 scale
    quality_score = db.Column(db.Float)  # 1-10 scale
    teamwork_score = db.Column(db.Float)  # 1-10 scale
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_on_time = db.Column(db.Integer, default=0)
    customer_feedback_score = db.Column(db.Float)
    manager_notes = db.Column(db.Text)
    evaluated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    staff = db.relationship('User', foreign_keys=[staff_id], backref='performance_evaluations')
    evaluator = db.relationship('User', foreign_keys=[evaluated_by], backref='staff_evaluations_given')


# ============================================
# INVENTORY MANAGEMENT MODELS
# ============================================

class InventoryCategory(db.Model):
    """Categories for organizing inventory items"""
    __tablename__ = 'inventory_category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('InventoryItem', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<InventoryCategory {self.name}>'

class Supplier(db.Model):
    """Suppliers for inventory items"""
    __tablename__ = 'supplier'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    payment_terms = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('InventoryItem', backref='supplier', lazy='dynamic')
    transactions = db.relationship('InventoryTransaction', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f'<Supplier {self.name}>'

class Department(db.Model):
    """Hotel departments that consume inventory"""
    __tablename__ = 'department'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('InventoryTransaction', 
                                  foreign_keys='InventoryTransaction.department_id',
                                  backref='department', lazy='dynamic')
    
    def __repr__(self):
        return f'<Department {self.name}>'

class InventoryItem(db.Model):
    """Individual inventory items tracked in the system"""
    __tablename__ = 'inventory_item'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('inventory_category.id'), nullable=False)
    unit_of_measure = db.Column(db.String(50), nullable=False)  # 'pieces', 'liters', 'kg', etc.
    current_stock = db.Column(db.Float, nullable=False, default=0.0)
    reorder_point = db.Column(db.Float, nullable=False)
    preferred_supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    unit_cost = db.Column(db.Float)
    last_restocked_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')  # 'active', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('InventoryTransaction', backref='item', lazy='dynamic')
    alerts = db.relationship('LowStockAlert', backref='item', lazy='dynamic')
    booking_reservations = db.relationship('BookingInventoryReservation', backref='item', lazy='dynamic')
    
    # Unique constraint: name must be unique within a category
    __table_args__ = (db.UniqueConstraint('name', 'category_id', name='_item_category_uc'),)
    
    @property
    def is_low_stock(self):
        """Check if item is below reorder point"""
        return self.current_stock < self.reorder_point
    
    @property
    def stock_status(self):
        """Get stock status string"""
        if self.current_stock == 0:
            return 'out_of_stock'
        elif self.is_low_stock:
            return 'low_stock'
        else:
            return 'in_stock'
    
    def __repr__(self):
        return f'<InventoryItem {self.name}>'

class InventoryTransaction(db.Model):
    """Records all inventory movements"""
    __tablename__ = 'inventory_transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'receipt', 'usage', 'transfer', 'adjustment'
    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float)  # For receipts
    total_cost = db.Column(db.Float)  # For receipts
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    source_department_id = db.Column(db.Integer, db.ForeignKey('department.id'))  # For transfers
    destination_department_id = db.Column(db.Integer, db.ForeignKey('department.id'))  # For transfers
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))  # For receipts
    adjustment_reason = db.Column(db.Text)  # For adjustments
    old_quantity = db.Column(db.Float)  # For adjustments
    new_quantity = db.Column(db.Float)  # For adjustments
    notes = db.Column(db.Text)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='inventory_transactions')
    source_department = db.relationship('Department', foreign_keys=[source_department_id])
    destination_department = db.relationship('Department', foreign_keys=[destination_department_id])
    
    @property
    def variance(self):
        """Calculate variance for adjustments"""
        if self.transaction_type == 'adjustment' and self.old_quantity is not None and self.new_quantity is not None:
            return self.new_quantity - self.old_quantity
        return None
    
    def __repr__(self):
        return f'<InventoryTransaction {self.id} - {self.transaction_type}>'

class LowStockAlert(db.Model):
    """Alerts for items below reorder point"""
    __tablename__ = 'low_stock_alert'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    alert_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    current_stock = db.Column(db.Float, nullable=False)
    reorder_point = db.Column(db.Float, nullable=False)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    acknowledged_at = db.Column(db.DateTime)
    
    # Relationships
    acknowledger = db.relationship('User', backref='acknowledged_alerts')
    
    def __repr__(self):
        return f'<LowStockAlert {self.id} - Item {self.item_id}>'

class BookingInventoryReservation(db.Model):
    """Links bookings to inventory reservations"""
    __tablename__ = 'booking_inventory_reservation'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    quantity_reserved = db.Column(db.Float, nullable=False)
    quantity_consumed = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='reserved')  # 'reserved', 'consumed', 'released'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    consumed_at = db.Column(db.DateTime)
    
    # Relationships
    booking = db.relationship('Booking', backref='inventory_reservations')
    
    def __repr__(self):
        return f'<BookingInventoryReservation {self.id}>'


# ============================================
# REFUND MANAGEMENT SYSTEM
# ============================================

class RefundRequest(db.Model):
    """User-initiated refund requests for cancelled bookings"""
    __tablename__ = 'refund_request'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Request details
    full_name = db.Column(db.String(200), nullable=False)
    refund_amount = db.Column(db.Float, nullable=False)
    gcash_number = db.Column(db.String(20), nullable=False)
    payment_receipt_url = db.Column(db.String(500))  # Screenshot of payment receipt
    reason = db.Column(db.Text)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # 'pending', 'processing', 'completed', 'rejected'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('refund_request', uselist=False))
    user = db.relationship('User', backref='refund_requests')
    response = db.relationship('RefundResponse', backref='request', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<RefundRequest {self.id} - Booking {self.booking_id}>'

class RefundResponse(db.Model):
    """Admin response to refund requests"""
    __tablename__ = 'refund_response'
    
    id = db.Column(db.Integer, primary_key=True)
    refund_request_id = db.Column(db.Integer, db.ForeignKey('refund_request.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Refund calculation
    original_amount = db.Column(db.Float, nullable=False)
    cancellation_fee = db.Column(db.Float, default=0.0)
    refunded_amount = db.Column(db.Float, nullable=False)
    
    # GCash refund proof
    gcash_screenshot_url = db.Column(db.String(500))  # Admin's screenshot of GCash refund
    gcash_reference_number = db.Column(db.String(100))
    
    # Status
    refund_status = db.Column(db.String(20), default='pending')  # 'pending', 'confirmed', 'failed'
    admin_notes = db.Column(db.Text)
    
    # User confirmation
    user_confirmed = db.Column(db.Boolean, default=False)
    user_confirmation_status = db.Column(db.String(20))  # 'confirmed', 'failed'
    user_confirmation_date = db.Column(db.DateTime)
    user_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    admin = db.relationship('User', backref='refund_responses')
    
    def __repr__(self):
        return f'<RefundResponse {self.id} - Request {self.refund_request_id}>'


# ============================================
# EXTRA SERVICES / SERVICE REQUESTS
# ============================================

class ServiceRequest(db.Model):
    """Guest requests for extra services (from inventory)"""
    __tablename__ = 'service_request'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    
    # Service details
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)  # Price at time of request
    total_fee = db.Column(db.Float, nullable=False)  # quantity × unit_price
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'confirmed', 'failed'
    
    # Timestamps
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    
    # Admin notes
    admin_notes = db.Column(db.Text)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Staff who processed
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('service_requests', lazy='dynamic'))
    user = db.relationship('User', foreign_keys=[user_id], backref='service_requests')
    inventory_item = db.relationship('InventoryItem', backref='service_requests')
    processor = db.relationship('User', foreign_keys=[processed_by], backref='processed_services')
    
    def __repr__(self):
        return f'<ServiceRequest {self.id} - Booking {self.booking_id} - {self.inventory_item.name if self.inventory_item else "Unknown"}>'
