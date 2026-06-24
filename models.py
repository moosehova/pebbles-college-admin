
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# --- SCHOOL ANNOUNCEMENT FEED ---
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_file = db.Column(db.String(20), nullable=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    # NEW FIELDS for Parent Portal
    role = db.Column(db.String(20), default='parent') # 'admin' or 'parent'
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    profile_pic = db.Column(db.String(255), default='default.png')

class Environment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50))
    students = db.relationship('Student', backref='classroom', lazy=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date)
    pickup_auth = db.Column(db.Text)
    tuition_fee = db.Column(db.Float, default=5000.0)
    class_id = db.Column(db.Integer, db.ForeignKey('environment.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    attendance = db.relationship('Attendance', backref='student', lazy=True)
    observations = db.relationship('Observation', backref='student', lazy=True)
    behavior_logs = db.relationship('BehaviorLog', backref='student', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.String(20)) # 'Present', 'Absent', 'Excused'
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))


class AttendanceIntervention(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False, default='Call Logged')
    note = db.Column(db.Text, nullable=False)
    expected_return_date = db.Column(db.Date, nullable=True)
    meeting_date = db.Column(db.Date, nullable=True)
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', backref='attendance_interventions', lazy=True)
    actor = db.relationship('User', backref='attendance_interventions', lazy=True)


class Observation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    note = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)
    term = db.Column(db.String(50), nullable=False, default='Term 1')
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref='grades', lazy=True)


class BehaviorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # Merit or Demerit
    category = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=1)
    note = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- FINANCE: Income Model ---
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='fees', lazy=True)

# --- FINANCE: Expense Model ---
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)

# --- INVENTORY: Asset Tracking ---
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    condition = db.Column(db.String(20), default='Good')  # New, Good, Damaged, Lost
    unit_value = db.Column(db.Float, default=0.0)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# --- HR: Staff Model ---
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50)) # e.g., Teacher, Admin, Security
    salary_amount = db.Column(db.Float)


class PayrollRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer, nullable=False)
    gross_salary = db.Column(db.Float, nullable=False)
    role_factor = db.Column(db.Float, default=1.0)
    deduction_amount = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='processed')
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    staff = db.relationship('Staff', backref='payroll_records', lazy=True)

# --- SOCIAL: Direct Messaging ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')


class EventAttendance(db.Model):
    """Tracks parent/student RSVPs to school events (Sports Day, Open Day, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('school_event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    rsvp_status = db.Column(db.String(20), default='pending')  # pending, attending, not_attending, maybe
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = db.relationship('SchoolEvent', backref='attendances', lazy=True)
    user = db.relationship('User', backref='event_attendances', lazy=True)
    student = db.relationship('Student', backref='event_attendances', lazy=True)


class SchoolSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(200), default='Pebbles College')
    school_logo = db.Column(db.String(200), default='logo.png')
    currency_symbol = db.Column(db.String(10), default='K')
    academic_year = db.Column(db.String(50), default='2026')


class SchoolEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    category = db.Column(db.String(50))  # 'Holiday', 'Exam', 'Sport', 'Academic'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
