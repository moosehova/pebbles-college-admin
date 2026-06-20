# ------------------- IMPORTS -------------------
import os
from io import BytesIO

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from sqlalchemy import inspect, text, or_
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from models import db, User, Student, Environment, Attendance, Observation, Income, Expense, Inventory, Staff, PayrollRecord, Message, AttendanceIntervention, Grade, BehaviorLog, SchoolSettings, SchoolEvent, EventAttendance

# ------------------- APP INITIALIZATION -------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
db.init_app(app)

# ------------------- LOGIN MANAGER -------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

schema_initialized = False


def seed_calendar_events():
    """Seed calendar with standard academic events if not already present."""
    if SchoolEvent.query.count() == 0:
        # Standard academic calendar for 2026
        sample_events = [
            SchoolEvent(
                title='Term 1 Begins',
                description='Start of the academic year',
                start_date=datetime(2026, 1, 15),
                category='Academic'
            ),
            SchoolEvent(
                title='Term 1 Exams',
                description='Mid-term examinations',
                start_date=datetime(2026, 3, 10),
                end_date=datetime(2026, 3, 20),
                category='Exam'
            ),
            SchoolEvent(
                title='Term 2 Begins',
                description='Start of second term',
                start_date=datetime(2026, 4, 1),
                category='Academic'
            ),
            SchoolEvent(
                title='Sports Day',
                description='Annual inter-house sports competition',
                start_date=datetime(2026, 5, 15),
                category='Sport'
            ),
            SchoolEvent(
                title='Mid-Year Break',
                description='Two-week holiday',
                start_date=datetime(2026, 6, 1),
                end_date=datetime(2026, 6, 15),
                category='Holiday'
            ),
            SchoolEvent(
                title='Term 2 Exams',
                description='Mid-year examinations',
                start_date=datetime(2026, 7, 5),
                end_date=datetime(2026, 7, 15),
                category='Exam'
            ),
            SchoolEvent(
                title='Term 3 Begins',
                description='Start of third term',
                start_date=datetime(2026, 8, 1),
                category='Academic'
            ),
            SchoolEvent(
                title='Open Day',
                description='Parents and prospective students welcome',
                start_date=datetime(2026, 9, 20),
                category='Academic'
            ),
            SchoolEvent(
                title='Year-End Exams',
                description='Final examinations of the year',
                start_date=datetime(2026, 10, 15),
                end_date=datetime(2026, 10, 28),
                category='Exam'
            ),
            SchoolEvent(
                title='Graduation Ceremony',
                description='End of year celebration',
                start_date=datetime(2026, 11, 20),
                category='Academic'
            ),
            SchoolEvent(
                title='Year-End Holiday',
                description='Month-long holiday',
                start_date=datetime(2026, 12, 1),
                end_date=datetime(2026, 12, 31),
                category='Holiday'
            ),
        ]
        db.session.add_all(sample_events)
        db.session.commit()


def seed_demo_data(profile='realistic'):
    """Populate Year-1 demo data (Jan 2025 to now) without overwriting existing tables."""
    profile = (profile or 'realistic').strip().lower()
    if profile not in ['realistic', 'profitable']:
        profile = 'realistic'

    current_month_anchor = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cursor = datetime(2025, 1, 1)
    month_windows = []
    while month_cursor <= current_month_anchor:
        month_windows.append(month_cursor)
        if month_cursor.month == 12:
            month_cursor = datetime(month_cursor.year + 1, 1, 1)
        else:
            month_cursor = datetime(month_cursor.year, month_cursor.month + 1, 1)

    env_map = {}
    if Environment.query.count() == 0:
        environments = [
            Environment(name='ELC', level='Early Learning Center'),
            Environment(name='Primary', level='Primary'),
            Environment(name='Secondary', level='Secondary'),
        ]
        db.session.add_all(environments)
        db.session.flush()
        env_map = {env.name: env for env in environments}
    else:
        env_map = {env.name: env for env in Environment.query.all()}

    students = []
    if Student.query.count() == 0:
        student_seed = [
            ('Camilla', 'Chitoti', 'ELC', 5000),
            ('Musole', 'Banda', 'ELC', 5000),
            ('Natasha', 'Phiri', 'ELC', 4900),
            ('Tapiwa', 'Zulu', 'ELC', 5100),
            ('Luyando', 'Mumba', 'ELC', 4950),
            ('Brian', 'Mwale', 'Primary', 6200),
            ('Amina', 'Kabaso', 'Primary', 6200),
            ('Kondwani', 'Sitali', 'Primary', 6000),
            ('Elina', 'Mbewe', 'Primary', 6150),
            ('Chisomo', 'Mwanza', 'Primary', 6100),
            ('Ruth', 'Chanda', 'Primary', 6000),
            ('Ian', 'Mulenga', 'Primary', 6050),
            ('Precious', 'Lungu', 'Primary', 6200),
            ('Mwaka', 'Tembo', 'Primary', 6100),
            ('Thandiwe', 'Njobvu', 'Primary', 6000),
            ('Mubanga', 'Silumesii', 'Secondary', 7600),
            ('Loveness', 'Zimba', 'Secondary', 7800),
            ('Misozi', 'Nkhoma', 'Secondary', 7700),
            ('Kundai', 'Chisala', 'Secondary', 7600),
            ('Martha', 'Sakala', 'Secondary', 7750),
            ('Charles', 'Mbewe', 'Secondary', 7650),
            ('Choolwe', 'Phiri', 'Secondary', 7900),
            ('Kelvin', 'Mutale', 'Secondary', 7500),
            ('Tracy', 'Lusaka', 'Secondary', 7800),
            ('Mubita', 'Munyinda', 'Secondary', 7700),
        ]
        for first_name, last_name, env_name, fee in student_seed:
            classroom = env_map.get(env_name)
            students.append(
                Student(
                    first_name=first_name,
                    last_name=last_name,
                    class_id=classroom.id if classroom else None,
                    tuition_fee=fee,
                )
            )
        db.session.add_all(students)
        db.session.flush()
    else:
        students = Student.query.all()

    if Attendance.query.count() == 0 and students:
        # Seed approx. one full term of attendance history (weekdays only).
        days_seeded = 0
        cursor = date.today() - timedelta(days=190)
        while cursor <= date.today() and days_seeded < 110:
            if cursor.weekday() < 5:
                for idx, student in enumerate(students):
                    marker = (idx + cursor.day + cursor.month) % 20
                    if marker <= 1:
                        status = 'Absent'
                    elif marker == 2:
                        status = 'Excused'
                    else:
                        status = 'Present'
                    db.session.add(Attendance(student_id=student.id, date=cursor, status=status))
                days_seeded += 1
            cursor += timedelta(days=1)

    if Grade.query.count() == 0 and students:
        terms = ['Term 1', 'Term 2', 'Term 3']
        subjects = ['Math', 'English', 'Science', 'ICT']
        for idx, student in enumerate(students):
            base = 54 + ((idx * 5) % 36)
            for term_index, term in enumerate(terms):
                for subject_index, subject in enumerate(subjects):
                    score = base + (term_index * 4) + (subject_index * 2) - (idx % 3)
                    db.session.add(
                        Grade(
                            student_id=student.id,
                            subject=subject,
                            score=max(38, min(98, score)),
                            term=term,
                            comment='Year-1 seeded score progression.'
                        )
                    )

    if BehaviorLog.query.count() == 0 and students:
        for idx, student in enumerate(students[:15]):
            db.session.add(
                BehaviorLog(
                    student_id=student.id,
                    type='Merit' if idx % 3 != 0 else 'Demerit',
                    category='Participation' if idx % 3 != 0 else 'Punctuality',
                    points=2 if idx % 3 != 0 else 1,
                    note='Year-1 seeded behavior signal.'
                )
            )

    if Staff.query.count() == 0:
        staff_seed = [
            ('Sarah Phiri', 'Lead Guide', 9400),
            ('Martin Zulu', 'Assistant', 5600),
            ('Joyce Tembo', 'Admin', 7000),
            ('Kelvin Banda', 'Security', 4600),
            ('Agnes Chisanga', 'Lead Guide', 9100),
        ]
        for name, role, salary in staff_seed:
            db.session.add(Staff(name=name, role=role, salary_amount=salary))
        db.session.flush()

    if PayrollRecord.query.count() == 0:
        for month_start in month_windows:
            for member in Staff.query.all():
                factor = role_factor_for_payroll(member.role)
                gross = round((member.salary_amount or 0) * factor, 2)
                deduction = round(gross * 0.03, 2)
                net = round(gross - deduction, 2)
                db.session.add(
                    PayrollRecord(
                        staff_id=member.id,
                        period_year=month_start.year,
                        period_month=month_start.month,
                        gross_salary=gross,
                        role_factor=factor,
                        deduction_amount=deduction,
                        net_salary=net,
                        status='processed',
                        generated_at=month_start.replace(day=26, hour=9),
                        paid_at=month_start.replace(day=28, hour=14),
                    )
                )

    if Income.query.count() == 0 and students:
        base_collection = 0.78 if profile == 'realistic' else 0.96
        for month_index, month_start in enumerate(month_windows):
            seasonal = ((month_index % 4) - 1.5) * 0.03
            for idx, student in enumerate(students):
                payer_variation = ((idx % 5) - 2) * 0.04
                ratio = max(0.0, min(1.05, base_collection + seasonal + payer_variation))
                # Keep some late payers in realistic mode to trigger finance intelligence.
                if profile == 'realistic' and idx % 7 == 0:
                    ratio = max(0.0, ratio - 0.22)
                if profile == 'profitable' and idx % 11 == 0:
                    ratio = max(0.65, ratio - 0.08)
                if ratio <= 0:
                    continue
                db.session.add(
                    Income(
                        student_id=student.id,
                        amount=round((student.tuition_fee or 0) * ratio, 2),
                        method='Bank Transfer' if ratio >= 0.75 else 'Cash',
                        date=month_start.replace(day=18, hour=10, minute=(idx % 4) * 10),
                    )
                )

    if Inventory.query.count() == 0:
        inventory_seed = [
            ('Samsung Tablets', 'Electronics', 24, 'Damaged', 2500),
            ('Montessori Pink Tower Kits', 'Montessori', 14, 'Good', 850),
            ('Classroom Desks', 'Furniture', 72, 'Good', 430),
            ('Library Chairs', 'Furniture', 44, 'New', 320),
            ('Projector Units', 'Electronics', 4, 'Lost', 5600),
            ('Science Lab Microscopes', 'Electronics', 8, 'Good', 1800),
        ]
        for name, category, quantity, item_condition, unit_value in inventory_seed:
            db.session.add(
                Inventory(
                    name=name,
                    category=category,
                    quantity=quantity,
                    condition=item_condition,
                    unit_value=unit_value,
                    date=datetime(2025, 2, 5, 8, 0),
                )
            )

    if Expense.query.count() == 0:
        payroll_records = PayrollRecord.query.all()
        for record in payroll_records:
            expense_month = datetime(record.period_year, record.period_month, 1)
            db.session.add(
                Expense(
                    category='Salary',
                    amount=record.net_salary,
                    description=f'Payroll {expense_month.strftime("%b %Y")} - {record.staff.name}',
                    date=expense_month.replace(day=28, hour=14),
                )
            )
        for month_index, month_start in enumerate(month_windows):
            db.session.add(
                Expense(
                    category='Maintenance',
                    amount=2600 + (month_index % 3) * 400,
                    description='Facilities and equipment maintenance',
                    date=month_start.replace(day=12, hour=11),
                )
            )
            db.session.add(
                Expense(
                    category='Utilities',
                    amount=1800 + (month_index % 4) * 220,
                    description='Water and electricity',
                    date=month_start.replace(day=22, hour=15),
                )
            )

    db.session.commit()


def check_and_migrate_schema():
    """Safe startup migration checks for SQLite deployments without Alembic."""
    inspector = inspect(db.engine)

    if inspector.has_table('student'):
        student_columns = [column['name'] for column in inspector.get_columns('student')]
        if 'tuition_fee' not in student_columns:
            db.session.execute(text('ALTER TABLE student ADD COLUMN tuition_fee FLOAT DEFAULT 5000'))
            db.session.commit()

    if inspector.has_table('attendance_intervention'):
        intervention_columns = [column['name'] for column in inspector.get_columns('attendance_intervention')]
        if 'meeting_date' not in intervention_columns:
            db.session.execute(text('ALTER TABLE attendance_intervention ADD COLUMN meeting_date DATE'))
            db.session.commit()

    if inspector.has_table('inventory'):
        inventory_columns = [column['name'] for column in inspector.get_columns('inventory')]
        if 'condition' not in inventory_columns:
            db.session.execute(text("ALTER TABLE inventory ADD COLUMN condition VARCHAR(20) DEFAULT 'Good'"))
            db.session.commit()
        if 'unit_value' not in inventory_columns:
            db.session.execute(text('ALTER TABLE inventory ADD COLUMN unit_value FLOAT DEFAULT 0'))
            db.session.commit()


def clear_demo_tables():
    """Clear proposal/demo transactional tables in dependency-safe order."""
    EventAttendance.query.delete()
    Message.query.delete()
    AttendanceIntervention.query.delete()
    BehaviorLog.query.delete()
    Grade.query.delete()
    Observation.query.delete()
    Attendance.query.delete()
    Income.query.delete()
    Expense.query.delete()
    PayrollRecord.query.delete()
    Staff.query.delete()
    Inventory.query.delete()
    Student.query.delete()
    Environment.query.delete()
    SchoolEvent.query.delete()
    db.session.commit()


def ensure_database_schema():
    global schema_initialized
    if schema_initialized:
        return

    db.create_all()
    check_and_migrate_schema()

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Seed calendar events
    seed_calendar_events()
    seed_demo_data()

    schema_initialized = True


@app.before_request
def initialize_schema_once():
    ensure_database_schema()


@app.context_processor
def inject_school_settings():
    settings = SchoolSettings.query.first() or SchoolSettings()
    logo_version = int(datetime.utcnow().timestamp())
    return {
        'school_settings': settings,
        'school_config': settings,
        'school_logo_version': logo_version
    }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def role_factor_for_payroll(role):
    role_map = {
        'Lead Guide': 1.08,
        'Assistant': 1.0,
        'Admin': 1.03,
        'Security': 0.97,
    }
    return role_map.get((role or '').strip(), 1.0)


def month_window(reference_date):
    month_start = datetime(reference_date.year, reference_date.month, 1)
    if reference_date.month == 12:
        next_month = datetime(reference_date.year + 1, 1, 1)
    else:
        next_month = datetime(reference_date.year, reference_date.month + 1, 1)
    return month_start, next_month

# ------------------- ROUTES -------------------

# PWA: Serve service worker from root scope (required for full-app coverage)
@app.route('/sw.js')
def service_worker():
    response = app.send_static_file('sw.js')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Content-Type'] = 'application/javascript'
    return response


@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')


# Updated route to match form action in attendance.html
@app.route('/parent-portal')
@login_required
def parent_portal():
    if not hasattr(current_user, 'role') or current_user.role != 'parent':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    student = Student.query.get(current_user.student_id) if current_user.student_id else None
    if not student:
        flash('Parent account is not linked to a student profile yet.', 'danger')
        return redirect(url_for('logout'))

    week_ago = datetime.utcnow().date() - timedelta(days=7)
    weekly_merits = BehaviorLog.query.filter(
        BehaviorLog.student_id == student.id,
        BehaviorLog.type == 'Merit',
        BehaviorLog.timestamp >= datetime.combine(week_ago, datetime.min.time())
    ).count()

    recent_grades = Grade.query.filter_by(student_id=student.id).order_by(Grade.created_at.desc()).limit(8).all()
    avg_grade = round(sum(g.score for g in recent_grades) / len(recent_grades), 1) if recent_grades else 0

    if weekly_merits >= 3:
        proud_moment = 'Star Student Alert: Your child has been exceptionally helpful this week.'
    elif avg_grade >= 80:
        proud_moment = 'Academic Excellence: Strong results this week. Keep the study rhythm going.'
    else:
        proud_moment = 'Steady Progress: Daily attendance and encouragement are building long-term success.'

    # Fetch announcements and other info for parents
    from models import Announcement
    announcements = Announcement.query.order_by(Announcement.date_posted.desc()).all()
    return render_template(
        'parent/portal.html',
        announcements=announcements,
        student=student,
        proud_moment=proud_moment,
        weekly_merits=weekly_merits,
        avg_grade=avg_grade
    )
@app.route('/inbox')
@login_required
def inbox():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    # Fetch messages for the admin (optional: filter by recipient)
    from models import Message
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template('admin/inbox.html', messages=messages)


@app.route('/parent/send-message', methods=['POST'])
@login_required
def send_message():
    if current_user.role != 'parent':
        return redirect(url_for('dashboard'))

    message_content = (request.form.get('message_content') or '').strip()
    if not message_content:
        flash('Message cannot be empty.', 'danger')
        return redirect(url_for('parent_portal'))

    admin = User.query.filter_by(role='admin').first()
    if not admin:
        flash('No administrator account is currently available.', 'danger')
        return redirect(url_for('parent_portal'))

    message = Message(
        sender_id=current_user.id,
        receiver_id=admin.id,
        content=message_content
    )
    db.session.add(message)
    db.session.commit()
    flash('Message sent to school office.', 'success')
    return redirect(url_for('parent_portal'))
@app.route('/announcement/new', methods=['GET', 'POST'])
@login_required
def new_announcement():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        # Optionally handle image upload here
        from models import Announcement
        announcement = Announcement(
            title=title,
            content=content,
            author_id=current_user.id
        )
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement posted!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_post.html')
@app.route('/attendance')
@login_required
def attendance():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('parent_portal'))
    # Fetch all students and today's attendance records
    from datetime import date
    students = Student.query.all()
    today = date.today()
    attendance_records = Attendance.query.filter_by(date=today).all()
    return render_template('academics/attendance.html', students=students, attendance_records=attendance_records, today=today)
@app.route('/dashboard')
@login_required
def dashboard():
    # Gather statistics for the dashboard
    all_students = Student.query.all()
    students = Student.query.count()
    classes = Environment.query.count()
    staff_count = Staff.query.count()
    total_income = db.session.query(db.func.sum(Income.amount)).scalar() or 0
    total_expense = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    balance = total_income - total_expense
    expense_percent = 0
    if total_income > 0:
        expense_percent = round((total_expense / total_income) * 100)
    
    # === SMART ALERT: Exam Countdown & Fee Intelligence ===
    # Find upcoming exams
    upcoming_exam = SchoolEvent.query.filter(
        SchoolEvent.category == 'Exam',
        SchoolEvent.start_date >= datetime.utcnow()
    ).order_by(SchoolEvent.start_date.asc()).first()
    
    days_to_exam = None
    exam_title = None
    if upcoming_exam:
        days_to_exam = (upcoming_exam.start_date.date() - datetime.utcnow().date()).days
        exam_title = upcoming_exam.title
    
    # Count students with outstanding fees (fees > total income for that student)
    students_with_outstanding = 0
    for student in all_students:
        student_income = db.session.query(db.func.sum(Income.amount)).filter(Income.student_id == student.id).scalar() or 0
        if student.tuition_fee and student_income < student.tuition_fee:
            students_with_outstanding += 1

    now = datetime.utcnow()
    month_start, next_month = month_window(now)

    month_payroll_records = PayrollRecord.query.filter(
        PayrollRecord.period_year == now.year,
        PayrollRecord.period_month == now.month
    ).all()
    month_payroll_total = sum(record.net_salary or 0 for record in month_payroll_records)

    month_tuition_collected = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= month_start,
        Income.date < next_month
    ).scalar() or 0

    payroll_fee_ratio = None
    payroll_insight = 'Generate this month payrun to unlock payroll cashflow intelligence.'
    payroll_level = 'neutral'
    if month_tuition_collected > 0:
        payroll_fee_ratio = round((month_payroll_total / month_tuition_collected) * 100, 1)
        if payroll_fee_ratio >= 65:
            payroll_level = 'critical'
            payroll_insight = (
                f'Warning: Payroll is {payroll_fee_ratio}% of this month\'s collected fees. '
                f'Recommend delaying non-essential maintenance.'
            )
        elif payroll_fee_ratio >= 45:
            payroll_level = 'watch'
            payroll_insight = (
                f'Payroll is {payroll_fee_ratio}% of fees collected this month. '
                f'Monitor discretionary spending closely.'
            )
        else:
            payroll_level = 'healthy'
            payroll_insight = (
                f'Healthy payroll position: {payroll_fee_ratio}% of this month\'s fee collections.'
            )

    inventory_items = Inventory.query.all()
    total_inventory_units = sum(item.quantity or 0 for item in inventory_items)
    damaged_units = sum((item.quantity or 0) for item in inventory_items if (item.condition or 'Good') == 'Damaged')
    lost_units = sum((item.quantity or 0) for item in inventory_items if (item.condition or 'Good') == 'Lost')
    damaged_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in inventory_items if (item.condition or 'Good') == 'Damaged')
    lost_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in inventory_items if (item.condition or 'Good') == 'Lost')
    inventory_risk_value = round(damaged_value + lost_value, 2)
    inventory_risk_percent = round(((damaged_units + lost_units) / total_inventory_units) * 100, 1) if total_inventory_units else 0
    
    stats = {
        'students': students,
        'classes': classes,
        'income': total_income,
        'staff_count': staff_count,
        'balance': balance,
        'expense_percent': expense_percent,
        'days_to_exam': days_to_exam,
        'exam_title': exam_title,
        'students_with_outstanding': students_with_outstanding,
        'month_payroll_total': round(month_payroll_total, 2),
        'month_tuition_collected': round(month_tuition_collected, 2),
        'payroll_fee_ratio': payroll_fee_ratio,
        'payroll_insight': payroll_insight,
        'payroll_level': payroll_level,
        'inventory_risk_value': inventory_risk_value,
        'inventory_risk_percent': inventory_risk_percent,
        'damaged_units': damaged_units,
        'lost_units': lost_units
    }

    all_grades = Grade.query.all()
    passing_grades = [grade for grade in all_grades if grade.score >= 50]
    academic_pass_rate = round((len(passing_grades) / len(all_grades)) * 100, 1) if all_grades else 0

    class_avg_map = {}
    for grade in all_grades:
        classroom = grade.student.classroom
        if not classroom:
            continue
        class_name = classroom.name
        if class_name not in class_avg_map:
            class_avg_map[class_name] = []
        class_avg_map[class_name].append(grade.score)

    class_averages = {
        class_name: (sum(scores) / len(scores))
        for class_name, scores in class_avg_map.items()
        if scores
    }

    subject_avg_map = {}
    for grade in all_grades:
        subject_key = (grade.subject or 'General').strip()
        if subject_key not in subject_avg_map:
            subject_avg_map[subject_key] = []
        subject_avg_map[subject_key].append(grade.score)

    subject_averages = {
        subject: (sum(scores) / len(scores))
        for subject, scores in subject_avg_map.items()
        if scores
    }

    now = datetime.utcnow()
    recent_cutoff = now - timedelta(days=30)
    previous_cutoff = now - timedelta(days=60)

    subject_rows = []
    for subject in sorted(subject_averages.keys()):
        current_grades = Grade.query.filter(
            Grade.subject == subject,
            Grade.created_at >= recent_cutoff
        ).all()
        previous_grades = Grade.query.filter(
            Grade.subject == subject,
            Grade.created_at >= previous_cutoff,
            Grade.created_at < recent_cutoff
        ).all()

        current_avg = (sum(grade.score for grade in current_grades) / len(current_grades)) if current_grades else subject_averages[subject]
        previous_avg = (sum(grade.score for grade in previous_grades) / len(previous_grades)) if previous_grades else 0
        trend = current_avg - previous_avg

        if current_avg < 60:
            insight = 'Teacher workshop recommended.'
        elif trend > 0:
            insight = 'Department is improving.'
        else:
            insight = 'Hold steady and monitor.'

        subject_rows.append({
            'subject': subject,
            'avg': round(current_avg, 1),
            'trend': round(trend, 1),
            'insight': insight
        })

    subject_rows.sort(key=lambda row: row['avg'], reverse=True)

    top_subject = None
    bottom_subject = None
    if subject_averages:
        top_subject = max(subject_averages, key=subject_averages.get)
        bottom_subject = min(subject_averages, key=subject_averages.get)

    academic_insight = 'No grade data yet. Teachers can start entering marks to unlock smart academic insights.'
    if len(class_averages) >= 2:
        top_class = max(class_averages, key=class_averages.get)
        low_class = min(class_averages, key=class_averages.get)
        gap = class_averages[top_class] - class_averages[low_class]
        academic_insight = (
            f"{top_class} is overperforming by {gap:.1f}% compared to {low_class}. "
            f"Suggest a peer-mentoring session between teachers."
        )

    stats['academic_pass_rate'] = academic_pass_rate
    stats['academic_insight'] = academic_insight
    stats['top_subject'] = top_subject
    stats['top_subject_avg'] = round(subject_averages[top_subject], 1) if top_subject else None
    stats['bottom_subject'] = bottom_subject
    stats['bottom_subject_avg'] = round(subject_averages[bottom_subject], 1) if bottom_subject else None
    stats['subject_rows'] = subject_rows
    stats['subject_leaderboard_preview'] = subject_rows[:4]
    attendance_risks = []
    for student in all_students:
        # Consider the latest three attendance entries as the active streak window.
        recent_records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).limit(3).all()
        if len(recent_records) == 3 and all(record.status == 'Absent' for record in recent_records):
            latest_intervention = AttendanceIntervention.query.filter_by(student_id=student.id).order_by(AttendanceIntervention.created_at.desc()).first()
            if latest_intervention and latest_intervention.resolved and latest_intervention.updated_at and latest_intervention.updated_at.date() >= recent_records[0].date:
                continue

            if latest_intervention:
                intervention_action = latest_intervention.action
                intervention_note = latest_intervention.note
                intervention_resolved = latest_intervention.resolved
                meeting_date = latest_intervention.meeting_date
            else:
                intervention_action = 'No Action Logged'
                intervention_note = None
                intervention_resolved = False
                meeting_date = None

            attendance_risks.append({
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'last_absent_date': recent_records[0].date,
                'intervention_action': intervention_action,
                'intervention_note': intervention_note,
                'intervention_resolved': intervention_resolved,
                'meeting_date': meeting_date,
                'meeting_pending': bool(meeting_date and not intervention_resolved)
            })

    return render_template(
        'dashboard/index.html',
        stats=stats,
        students=all_students,
        attendance_risks=attendance_risks,
        attendance_risk_count=len(attendance_risks)
    )
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # You may want to redirect based on role here
        if hasattr(current_user, 'role') and current_user.role == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('parent_portal'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            if user.role == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('parent_portal'))
        else:
            flash('Invalid username or password', 'danger')

    featured_merit = BehaviorLog.query.filter_by(type='Merit').order_by(BehaviorLog.timestamp.desc()).first()
    merit_student = featured_merit.student if featured_merit else None
    if featured_merit and merit_student:
        login_highlight = {
            'title': 'Proud Parent Moment',
            'message': f"{merit_student.first_name} earned a {featured_merit.category} merit.",
            'detail': featured_merit.note or 'A teacher captured a positive moment worth celebrating today.'
        }
    else:
        login_highlight = {
            'title': 'Proud Parent Moment',
            'message': 'Merits, grades, and attendance now roll into one weekly family digest.',
            'detail': 'Log a Kindness merit first to light up the Pebbles Yellow notification flow.'
        }

    return render_template('login.html', login_highlight=login_highlight)
@app.route('/')
def home():
    if current_user.is_authenticated:
        if hasattr(current_user, 'role') and current_user.role == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('parent_portal'))
    return redirect(url_for('login'))
@app.route('/save_attendance', methods=['GET', 'POST'])
@login_required
def save_attendance():
    if request.method == 'GET':
        return redirect(url_for('attendance'))
    env_id = request.form.get('env_id')
    date_str = request.form.get('date')
    if not date_str:
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        date_obj = datetime.utcnow().date()
    for key in request.form:
        if key.startswith('status_'):
            student_id = key.split('_')[1]
            status = request.form.get(key)
            existing = Attendance.query.filter_by(student_id=student_id, date=date_obj).first()
            if existing:
                existing.status = status
            else:
                new_rec = Attendance(student_id=student_id, date=date_obj, status=status)
                db.session.add(new_rec)
    db.session.commit()
    flash("Daily Register Saved!", "success")
    return redirect(url_for('attendance', env_id=env_id, date=date_str))



# --- ACADEMICS ROUTES ---
@app.route('/academics/manage', methods=['GET'])
@login_required
def manage_academics():
    envs = Environment.query.all()
    return render_template('academics/manage.html', environments=envs)

@app.route('/academics/create_env', methods=['POST'])
@login_required
def create_env():
    new_env = Environment(name=request.form['name'], level=request.form['level'])
    db.session.add(new_env)
    db.session.commit()
    return redirect(url_for('manage_academics'))



# --- OBSERVATIONS (JOURNEY NOTES) ---
@app.route('/academics/observations', methods=['GET'])
@login_required
def observations():
    students = Student.query.all()
    all_obs = Observation.query.order_by(Observation.date.desc()).all()
    return render_template('academics/observations.html', students=students, observations=all_obs)

@app.route('/academics/save_observation', methods=['POST'])
@login_required
def save_observation():
    new_obs = Observation(
        student_id=request.form.get('student_id'),
        title=request.form.get('title'),
        note=request.form.get('note'),
        date=datetime.utcnow()
    )
    db.session.add(new_obs)
    db.session.commit()
    flash("Observation saved to the child's journey!", "success")
    return redirect(url_for('observations'))


@app.route('/academics/grades', methods=['GET'])
@login_required
def edit_grades():
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        return redirect(url_for('parent_portal'))

    students = Student.query.order_by(Student.first_name.asc()).all()
    term = request.args.get('term', 'Term 1')
    grades = Grade.query.filter_by(term=term).order_by(Grade.created_at.desc()).all()
    return render_template('admin/edit_grades.html', students=students, grades=grades, term=term)


@app.route('/academics/save-grade', methods=['POST'])
@login_required
def save_grade():
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        return redirect(url_for('parent_portal'))

    student_id = request.form.get('student_id')
    subject = (request.form.get('subject') or '').strip()
    score_raw = request.form.get('score')
    term = (request.form.get('term') or 'Term 1').strip()
    comment = (request.form.get('comment') or '').strip()

    if not student_id or not subject or score_raw is None:
        flash('Student, subject, and score are required.', 'danger')
        return redirect(url_for('edit_grades', term=term))

    try:
        score = float(score_raw)
    except ValueError:
        flash('Score must be a valid number.', 'danger')
        return redirect(url_for('edit_grades', term=term))

    if score < 0 or score > 100:
        flash('Score must be between 0 and 100.', 'danger')
        return redirect(url_for('edit_grades', term=term))

    grade = Grade(
        student_id=student_id,
        subject=subject,
        score=score,
        term=term,
        comment=comment or None
    )
    db.session.add(grade)
    db.session.commit()

    flash('Grade saved successfully.', 'success')
    return redirect(url_for('edit_grades', term=term))


@app.route('/api/suggest-comment/<int:student_id>')
@login_required
def suggest_comment(student_id):
    grades = Grade.query.filter_by(student_id=student_id).all()
    if not grades:
        return jsonify({'suggestion': 'No academic data available yet.'})

    avg = sum(grade.score for grade in grades) / len(grades)
    if avg >= 85:
        suggestion = 'An exceptional term. Demonstrates mastery of core concepts and shows great leadership in class.'
    elif avg >= 70:
        suggestion = 'Strong performance. Consistent effort is paying off; encouraged to participate more in discussions.'
    elif avg >= 50:
        suggestion = 'Satisfactory progress, though some topics remain challenging. Targeted revision is recommended.'
    else:
        suggestion = 'Needs urgent attention. Significant gaps in understanding detected; intervention meeting advised.'

    return jsonify({'suggestion': suggestion})


# --- PEOPLE ROUTES ---
@app.route('/people/add_student', methods=['GET', 'POST'])
@login_required
def enroll_student():
    if request.method == 'POST':
        # Convert string date from form to Python date object
        dob_obj = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
        new_student = Student(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            dob=dob_obj,
            class_id=request.form['class_id'],
            pickup_auth=request.form['pickup_auth']
        )
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('dashboard'))
    envs = Environment.query.all()
    return render_template('people/add_student.html', environments=envs)



# --- PROMOTION HUB ---
@app.route('/academics/promotion')
@login_required
def promotion_hub():
    envs = Environment.query.all()
    return render_template('academics/promotion.html', environments=envs)


# --- CREATE PARENT ACCOUNT ---
@app.route('/people/create-parent', methods=['GET', 'POST'])
@login_required
def create_parent():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Use werkzeug's generate_password_hash for consistency
        hashed_pw = generate_password_hash(request.form.get('password'))
        new_parent = User(
            username=request.form.get('username'),
            password=hashed_pw,
            role='parent',
            student_id=request.form.get('student_id')
        )
        db.session.add(new_parent)
        db.session.commit()
        flash("Parent account created successfully!", "success")
        return redirect(url_for('dashboard'))
    all_students = Student.query.all()
    return render_template('people/add_parent.html', students=all_students)


@app.route('/people/report/<int:student_id>')
@login_required
def view_report(student_id):
    student = Student.query.get_or_404(student_id)
    now = datetime.utcnow()
    # 1. Calculate Attendance %
    total_days = Attendance.query.filter_by(student_id=student_id).count()
    present_days = Attendance.query.filter_by(student_id=student_id, status='Present').count()
    att_percent = 0
    if total_days > 0:
        att_percent = round((present_days / total_days) * 100)
    # 2. Get Journey Notes for this month
    observations = Observation.query.filter(
        Observation.student_id == student_id,
        Observation.date >= now.replace(day=1)
    ).all()
    return render_template('people/report.html', 
                           student=student, 
                           att_percent=att_percent, 
                           observations=observations,
                           month_name=now.strftime('%B'),
                           year=now.year)


@app.route('/student/profile/<int:student_id>')
@login_required
def student_profile(student_id):
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        flash('Student 360 is available to school staff only.', 'danger')
        return redirect(url_for('parent_portal'))

    student = Student.query.get_or_404(student_id)
    recent_attendance = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc()).limit(10).all()
    grades = Grade.query.filter_by(student_id=student_id).order_by(Grade.created_at.desc()).all()
    merits = BehaviorLog.query.filter_by(student_id=student_id, type='Merit').order_by(BehaviorLog.timestamp.desc()).all()
    demerits = BehaviorLog.query.filter_by(student_id=student_id, type='Demerit').order_by(BehaviorLog.timestamp.desc()).all()
    observations = Observation.query.filter_by(student_id=student_id).order_by(Observation.date.desc()).limit(5).all()

    total_paid = sum(payment.amount for payment in student.fees)
    balance = round((student.tuition_fee or 0) - total_paid, 2)
    total_days = Attendance.query.filter_by(student_id=student_id).count()
    present_days = Attendance.query.filter_by(student_id=student_id, status='Present').count()
    attendance_rate = round((present_days / total_days) * 100, 1) if total_days else 0
    avg_grade = round(sum(grade.score for grade in grades) / len(grades), 1) if grades else 0
    merit_points = sum(entry.points for entry in merits)
    demerit_points = sum(entry.points for entry in demerits)

    if demerit_points >= 3:
        profile_signal = 'Behavior support recommended. Review patterns before the next parent touchpoint.'
        profile_tone = 'risk'
    elif balance > 0:
        profile_signal = 'Finance follow-up needed. The student profile shows an outstanding fee balance.'
        profile_tone = 'finance'
    elif avg_grade >= 80 and merit_points >= 3:
        profile_signal = 'Student is performing strongly across academics and character metrics.'
        profile_tone = 'strong'
    else:
        profile_signal = 'Steady profile. Monitor attendance rhythm and continue recording live interventions.'
        profile_tone = 'steady'

    return render_template(
        'admin/student_profile.html',
        student=student,
        attendance=recent_attendance,
        grades=grades,
        merits=merits,
        demerits=demerits,
        observations=observations,
        balance=balance,
        total_paid=round(total_paid, 2),
        attendance_rate=attendance_rate,
        avg_grade=avg_grade,
        merit_points=merit_points,
        demerit_points=demerit_points,
        profile_signal=profile_signal,
        profile_tone=profile_tone
    )


@app.route('/search-student')
@login_required
def search_student():
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        return redirect(url_for('parent_portal'))

    query = (request.args.get('q') or '').strip()
    if not query:
        flash('Type a student name first.', 'warning')
        return redirect(request.referrer or url_for('dashboard'))

    like_query = f"%{query}%"
    students = Student.query.filter(
        or_(
            Student.first_name.ilike(like_query),
            Student.last_name.ilike(like_query)
        )
    ).order_by(Student.first_name.asc(), Student.last_name.asc()).all()

    if len(students) == 1:
        return redirect(url_for('student_profile', student_id=students[0].id))

    if len(students) > 1:
        return redirect(url_for('view_students', q=query))

    flash(f"No student found matching '{query}'.", 'warning')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/api/search-autocomplete')
@login_required
def search_autocomplete():
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        return jsonify([])

    query = (request.args.get('q') or '').strip()
    if len(query) < 2:
        return jsonify([])

    like_query = f"%{query}%"
    students = Student.query.filter(
        or_(
            Student.first_name.ilike(like_query),
            Student.last_name.ilike(like_query)
        )
    ).order_by(Student.first_name.asc(), Student.last_name.asc()).limit(6).all()

    return jsonify([
        {
            'id': student.id,
            'name': f"{student.first_name} {student.last_name}",
            'environment': student.classroom.name if student.classroom else 'General'
        }
        for student in students
    ])


@app.route('/students')
@login_required
def view_students():
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        return redirect(url_for('parent_portal'))

    query = (request.args.get('q') or '').strip()
    selected_env_id = (request.args.get('env_id') or '').strip()

    students_query = Student.query
    if selected_env_id.isdigit():
        students_query = students_query.filter(Student.class_id == int(selected_env_id))

    if query:
        like_query = f"%{query}%"
        students_query = students_query.filter(
            or_(
                Student.first_name.ilike(like_query),
                Student.last_name.ilike(like_query)
            )
        )

    students = students_query.order_by(Student.first_name.asc(), Student.last_name.asc()).all()
    environments = Environment.query.order_by(Environment.name.asc()).all()

    student_rows = []
    for student in students:
        total_paid = sum(payment.amount for payment in student.fees)
        balance = round((student.tuition_fee or 0) - total_paid, 2)

        recent_attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).limit(3).all()
        attendance_risk = len(recent_attendance) == 3 and all(record.status == 'Absent' for record in recent_attendance)

        demerit_points = db.session.query(db.func.sum(BehaviorLog.points)).filter(
            BehaviorLog.student_id == student.id,
            BehaviorLog.type == 'Demerit'
        ).scalar() or 0

        tags = []
        if balance <= 0:
            tags.append({'label': 'Paid', 'tone': 'paid'})
        else:
            tags.append({'label': 'Outstanding', 'tone': 'finance'})

        if attendance_risk or demerit_points >= 3:
            tags.append({'label': 'At Risk', 'tone': 'risk'})
        else:
            tags.append({'label': 'Stable', 'tone': 'stable'})

        student_rows.append({
            'student': student,
            'balance': balance,
            'tags': tags
        })

    return render_template(
        'admin/student_list.html',
        student_rows=student_rows,
        query=query,
        environments=environments,
        selected_env_id=selected_env_id
    )


@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def school_settings():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    settings = SchoolSettings.query.first()
    if not settings:
        settings = SchoolSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.school_name = (request.form.get('school_name') or settings.school_name or 'Pebbles College').strip()
        settings.currency_symbol = (request.form.get('currency_symbol') or settings.currency_symbol or 'K').strip()[:10]
        settings.academic_year = (request.form.get('academic_year') or settings.academic_year or '').strip()

        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo_file.save(file_path)
                settings.school_logo = filename
            else:
                flash('Logo must be PNG, JPG, JPEG, WEBP, or GIF.', 'danger')
                return redirect(url_for('school_settings'))

        db.session.add(settings)
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('school_settings'))

    return render_template('admin/settings.html', settings=settings)


@app.route('/admin/import-students', methods=['POST'])
@login_required
def import_students():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    uploaded_file = request.files.get('csv_file')
    if not uploaded_file or not uploaded_file.filename:
        flash('Please upload a CSV or Excel file first.', 'warning')
        return redirect(url_for('school_settings'))

    filename = uploaded_file.filename.lower()
    import pandas as pd

    try:
        if filename.endswith('.csv'):
            dataframe = pd.read_csv(uploaded_file)
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            dataframe = pd.read_excel(uploaded_file)
        else:
            flash('Unsupported file type. Use CSV, XLSX, or XLS.', 'danger')
            return redirect(url_for('school_settings'))
    except Exception:
        flash('Unable to read file. Check the format and try again.', 'danger')
        return redirect(url_for('school_settings'))

    def normalize(value):
        return (str(value).strip() if value is not None else '')

    imported = 0
    skipped = 0
    for _, row in dataframe.iterrows():
        first_name = normalize(row.get('first_name'))
        last_name = normalize(row.get('last_name'))

        full_name = normalize(row.get('name'))
        if (not first_name or not last_name) and full_name:
            split_name = [piece for piece in full_name.split() if piece]
            if split_name and not first_name:
                first_name = split_name[0]
            if len(split_name) > 1 and not last_name:
                last_name = ' '.join(split_name[1:])

        if not first_name:
            skipped += 1
            continue
        if not last_name:
            last_name = 'Student'

        fee_raw = row.get('fee', row.get('tuition_fee', 5000))
        try:
            tuition_fee = float(fee_raw) if normalize(fee_raw) else 5000.0
        except (TypeError, ValueError):
            tuition_fee = 5000.0

        env_name = normalize(row.get('environment') or row.get('classroom') or row.get('class'))
        env_obj = None
        if env_name:
            env_obj = Environment.query.filter(Environment.name.ilike(env_name)).first()
            if not env_obj:
                env_obj = Environment(name=env_name, level='General')
                db.session.add(env_obj)
                db.session.flush()

        duplicate = Student.query.filter_by(first_name=first_name, last_name=last_name, class_id=env_obj.id if env_obj else None).first()
        if duplicate:
            skipped += 1
            continue

        new_student = Student(
            first_name=first_name,
            last_name=last_name,
            class_id=env_obj.id if env_obj else None,
            tuition_fee=tuition_fee
        )
        db.session.add(new_student)
        imported += 1

    db.session.commit()
    flash(f'Student import complete: {imported} added, {skipped} skipped.', 'success')
    return redirect(url_for('school_settings'))


@app.route('/admin/reset-demo-data', methods=['POST'])
@login_required
def reset_demo_data():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    confirmation = (request.form.get('confirmation') or '').strip().upper()
    if confirmation != 'RESET DEMO':
        flash('Reset cancelled. Type RESET DEMO to confirm.', 'warning')
        return redirect(url_for('school_settings'))

    clear_demo_tables()

    seed_calendar_events()
    seed_demo_data()
    flash('Demo data reset complete. Intelligence modules are ready for proposal walkthrough.', 'success')
    return redirect(url_for('school_settings'))


@app.route('/admin/seed-demo-full')
@login_required
def seed_demo_full_route():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    profile = (request.args.get('profile') or 'realistic').strip().lower()
    if profile not in ['realistic', 'profitable']:
        profile = 'realistic'

    clear_demo_tables()
    seed_calendar_events()
    seed_demo_data(profile=profile)

    flash(
        f'Full Year demo refresh complete ({profile} profile). Dashboard and Student 360 are now fully populated.',
        'success'
    )
    return redirect(url_for('dashboard'))


@app.route('/admin/seed-demo')
@login_required
def seed_demo_route():
    if hasattr(current_user, 'role') and current_user.role != 'admin':
        return redirect(url_for('dashboard'))

    profile = (request.args.get('profile') or 'realistic').strip().lower()
    if profile not in ['realistic', 'profitable']:
        profile = 'realistic'

    before_counts = {
        'students': Student.query.count(),
        'staff': Staff.query.count(),
        'inventory': Inventory.query.count(),
        'grades': Grade.query.count(),
        'income': Income.query.count(),
        'payroll': PayrollRecord.query.count(),
    }

    seed_calendar_events()
    seed_demo_data(profile=profile)

    after_counts = {
        'students': Student.query.count(),
        'staff': Staff.query.count(),
        'inventory': Inventory.query.count(),
        'grades': Grade.query.count(),
        'income': Income.query.count(),
        'payroll': PayrollRecord.query.count(),
    }

    inserted_total = sum(max(after_counts[key] - before_counts[key], 0) for key in before_counts)
    if inserted_total > 0:
        flash(
            (
                f'Year-1 demo data seeded ({profile} profile): +{after_counts["students"] - before_counts["students"]} students, '
                f'+{after_counts["staff"] - before_counts["staff"]} staff, '
                f'+{after_counts["inventory"] - before_counts["inventory"]} inventory items, '
                f'+{after_counts["grades"] - before_counts["grades"]} grades, '
                f'+{after_counts["payroll"] - before_counts["payroll"]} payroll records.'
            ),
            'success'
        )
    else:
        flash('Demo data already exists. Use Reset Demo Data in Settings for a fresh Year-1 dataset before reseeding.', 'info')

    return redirect(url_for('dashboard'))


@app.route('/behavior/log', methods=['POST'])
@login_required
def log_behavior():
    if hasattr(current_user, 'role') and current_user.role == 'parent':
        return redirect(url_for('parent_portal'))

    student_id = request.form.get('student_id')
    behavior_type = (request.form.get('type') or 'Merit').strip()
    category = (request.form.get('category') or 'Kindness').strip()
    points_raw = request.form.get('points') or '1'
    note = (request.form.get('note') or '').strip()

    try:
        points = int(points_raw)
    except ValueError:
        points = 1

    if behavior_type not in ['Merit', 'Demerit']:
        behavior_type = 'Merit'

    entry = BehaviorLog(
        student_id=student_id,
        type=behavior_type,
        category=category,
        points=points,
        note=note
    )
    db.session.add(entry)
    db.session.commit()
    flash(f'{behavior_type} logged for student.', 'success')
    return redirect(url_for('student_profile', student_id=student_id))


@app.route('/parent/weekly-digest/<int:student_id>')
@login_required
def weekly_digest(student_id):
    student = Student.query.get_or_404(student_id)
    if current_user.role == 'parent' and current_user.student_id != student.id:
        flash('Unauthorized digest access.', 'danger')
        return redirect(url_for('parent_portal'))

    week_start = datetime.utcnow().date() - timedelta(days=7)
    attendance_records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= week_start
    ).order_by(Attendance.date.desc()).all()
    present_count = sum(1 for record in attendance_records if record.status == 'Present')
    attendance_rate = round((present_count / len(attendance_records)) * 100, 1) if attendance_records else 0

    recent_grades = Grade.query.filter(
        Grade.student_id == student.id,
        Grade.created_at >= datetime.combine(week_start, datetime.min.time())
    ).order_by(Grade.created_at.desc()).all()
    avg_grade = round(sum(g.score for g in recent_grades) / len(recent_grades), 1) if recent_grades else 0

    merits = BehaviorLog.query.filter(
        BehaviorLog.student_id == student.id,
        BehaviorLog.type == 'Merit',
        BehaviorLog.timestamp >= datetime.combine(week_start, datetime.min.time())
    ).count()

    demerits = BehaviorLog.query.filter(
        BehaviorLog.student_id == student.id,
        BehaviorLog.type == 'Demerit',
        BehaviorLog.timestamp >= datetime.combine(week_start, datetime.min.time())
    ).count()

    if merits >= 3:
        nudge = 'Star Student Alert! Your child has been exceptionally helpful this week.'
        nudge_tone = 'star'
    elif avg_grade >= 80:
        nudge = 'Academic Excellence: Scoring among the strongest performers this week.'
        nudge_tone = 'academic'
    else:
        nudge = 'Steady Progress: Attendance momentum is building. Keep the daily routine strong.'
        nudge_tone = 'progress'

    return render_template(
        'parent/digest.html',
        student=student,
        nudge=nudge,
        nudge_tone=nudge_tone,
        attendance_rate=attendance_rate,
        avg_grade=avg_grade,
        merits=merits,
        demerits=demerits,
        recent_grades=recent_grades,
        attendance_records=attendance_records
    )


@app.route('/analytics/subjects')
@login_required
def subject_stats():
    if current_user.role not in ['admin', 'accountant']:
        return redirect(url_for('dashboard'))

    now = datetime.utcnow()
    window_start = now - timedelta(days=30)
    previous_start = now - timedelta(days=60)

    all_subjects = sorted({(grade.subject or 'General').strip() for grade in Grade.query.all()})
    stats_rows = []
    for subject in all_subjects:
        current_grades = Grade.query.filter(
            Grade.subject == subject,
            Grade.created_at >= window_start
        ).all()
        previous_grades = Grade.query.filter(
            Grade.subject == subject,
            Grade.created_at >= previous_start,
            Grade.created_at < window_start
        ).all()

        current_avg = (sum(g.score for g in current_grades) / len(current_grades)) if current_grades else 0
        previous_avg = (sum(g.score for g in previous_grades) / len(previous_grades)) if previous_grades else 0
        trend = current_avg - previous_avg

        if current_avg < 60:
            insight = 'AI Insight: Schedule teacher workshop and targeted support clinic.'
        elif trend > 0:
            insight = 'AI Insight: Positive trajectory. Capture and share best practices.'
        else:
            insight = 'AI Insight: Stable. Maintain revision cadence and monitor weekly tasks.'

        stats_rows.append({
            'subject': subject,
            'avg': round(current_avg, 1),
            'previous_avg': round(previous_avg, 1),
            'trend': round(trend, 1),
            'insight': insight,
            'sample_size': len(current_grades),
            'direction': 'up' if trend > 0 else 'down' if trend < 0 else 'flat'
        })

    stats_rows.sort(key=lambda row: row['avg'], reverse=True)
    return render_template('admin/subject_stats.html', subject_rows=stats_rows)


# --- FINANCE HUB ---
@app.route('/finance/fees', methods=['GET', 'POST'])
@login_required
def fee_collection():
    if request.method == 'POST':
        new_payment = Income(
            student_id=request.form.get('student_id'),
            amount=request.form.get('amount'),
            method=request.form.get('method'),
            date=datetime.utcnow()
        )
        db.session.add(new_payment)
        db.session.commit()
        flash("Fee payment recorded!", "success")
        return redirect(url_for('fee_collection'))
    students = Student.query.all()
    recent_fees = Income.query.order_by(Income.date.desc()).all()
    return render_template('finance/fees.html', students=students, fees=recent_fees)



# --- EXPENSES MODULE ---
@app.route('/finance/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    staff_list = Staff.query.all()
    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        description = request.form.get('description')
        staff_id = request.form.get('staff_id')
        if category == 'Salary' and staff_id:
            staff_member = Staff.query.get(staff_id)
            if staff_member:
                description = f"Salary payment for {staff_member.name}"
                amount = staff_member.salary_amount
        new_exp = Expense(
            category=category,
            amount=amount,
            description=description
        )
        db.session.add(new_exp)
        db.session.commit()
        flash("Expense recorded successfully!", "success")
        return redirect(url_for('expenses'))
    all_expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('finance/expenses.html', expenses=all_expenses, staff_list=staff_list)



# --- STAFF & PAYROLL HUB ---
@app.route('/finance/staff')
@login_required
def staff_hub():
    all_staff = Staff.query.all()
    now = datetime.utcnow()
    month_name = now.strftime('%B')

    payroll_records = PayrollRecord.query.filter(
        PayrollRecord.period_year == now.year,
        PayrollRecord.period_month == now.month
    ).order_by(PayrollRecord.generated_at.desc()).all()

    month_payroll_total = sum(record.net_salary or 0 for record in payroll_records)
    month_start, next_month = month_window(now)
    month_tuition_collected = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= month_start,
        Income.date < next_month
    ).scalar() or 0

    payroll_fee_ratio = round((month_payroll_total / month_tuition_collected) * 100, 1) if month_tuition_collected else None
    if payroll_fee_ratio is None:
        payroll_insight = 'No tuition has been collected this month yet. Run fee reminders before payrun approval.'
        insight_tone = 'watch'
    elif payroll_fee_ratio >= 65:
        payroll_insight = (
            f'Warning: Payroll is {payroll_fee_ratio}% of this month\'s collected fees. '
            f'Recommend delaying non-essential maintenance.'
        )
        insight_tone = 'critical'
    elif payroll_fee_ratio >= 45:
        payroll_insight = (
            f'Payroll is {payroll_fee_ratio}% of fee collections this month. '
            f'Proceed carefully with non-core expenses.'
        )
        insight_tone = 'watch'
    else:
        payroll_insight = f'Healthy payroll ratio at {payroll_fee_ratio}% of monthly fee collections.'
        insight_tone = 'healthy'

    return render_template(
        'finance/staff.html',
        staff=all_staff,
        payroll_records=payroll_records,
        month_name=month_name,
        month_payroll_total=round(month_payroll_total, 2),
        month_tuition_collected=round(month_tuition_collected, 2),
        payroll_fee_ratio=payroll_fee_ratio,
        payroll_insight=payroll_insight,
        insight_tone=insight_tone
    )

@app.route('/finance/staff/add', methods=['POST'])
@login_required
def add_staff():
    new_member = Staff(
        name=request.form.get('name'),
        role=request.form.get('role'),
        salary_amount=request.form.get('salary')
    )
    db.session.add(new_member)
    db.session.commit()
    flash(f"Staff member {new_member.name} registered!", "success")
    return redirect(url_for('staff_hub'))


@app.route('/finance/staff/payrun', methods=['POST'])
@login_required
def generate_payrun():
    deduction_percent_raw = request.form.get('deduction_percent', '0').strip()
    try:
        deduction_percent = max(0.0, min(float(deduction_percent_raw), 40.0))
    except ValueError:
        deduction_percent = 0.0

    now = datetime.utcnow()
    staff_members = Staff.query.all()
    created_count = 0
    skipped_count = 0

    for member in staff_members:
        existing = PayrollRecord.query.filter_by(
            staff_id=member.id,
            period_year=now.year,
            period_month=now.month
        ).first()
        if existing:
            skipped_count += 1
            continue

        role_factor = role_factor_for_payroll(member.role)
        gross_salary = round((member.salary_amount or 0) * role_factor, 2)
        deduction_amount = round(gross_salary * (deduction_percent / 100.0), 2)
        net_salary = round(gross_salary - deduction_amount, 2)

        record = PayrollRecord(
            staff_id=member.id,
            period_year=now.year,
            period_month=now.month,
            gross_salary=gross_salary,
            role_factor=role_factor,
            deduction_amount=deduction_amount,
            net_salary=net_salary,
            status='processed',
            paid_at=datetime.utcnow()
        )
        db.session.add(record)

        db.session.add(Expense(
            category='Salary',
            amount=net_salary,
            description=f'Auto Payrun {now.strftime("%B %Y")} - {member.name}'
        ))
        created_count += 1

    db.session.commit()
    flash(
        f'Payrun complete for {now.strftime("%B %Y")}: {created_count} generated, {skipped_count} already existed.',
        'success'
    )
    return redirect(url_for('staff_hub'))


# --- FINANCE: REMIND ALL PARENTS WITH OUTSTANDING BALANCE ---
@app.route('/finance/remind-all', methods=['POST'])
@login_required
def remind_all():
    if current_user.role not in ['admin', 'accountant']:
        return redirect(url_for('dashboard'))

    import sqlalchemy as sa
    from models import Message

    students = Student.query.all()
    sent = 0
    for student in students:
        total_paid = db.session.query(sa.func.sum(Income.amount)).filter(Income.student_id == student.id).scalar() or 0
        balance = (student.tuition_fee or 0) - total_paid
        if balance > 0:
            parent = User.query.filter_by(student_id=student.id, role='parent').first()
            if parent:
                msg = Message(
                    sender_id=current_user.id,
                    receiver_id=parent.id,
                    content=(
                        f"Dear Parent of {student.first_name} {student.last_name}, "
                        f"this is a friendly reminder that a fee balance of K{balance:,.2f} "
                        f"is currently outstanding. Please visit the school office at your earliest convenience. "
                        f"Thank you — Pebbles College Finance Office."
                    )
                )
                db.session.add(msg)
                sent += 1

    db.session.commit()
    flash(f"Reminder notification sent to {sent} parent(s) with outstanding balances.", "success")
    return redirect(url_for('finance_intelligence'))


# --- ATTENDANCE INTELLIGENCE: REMIND PARENTS OF AT-RISK STUDENTS ---
@app.route('/attendance/remind-risk', methods=['POST'])
@login_required
def remind_attendance_risks():
    if current_user.role not in ['admin', 'accountant']:
        return redirect(url_for('dashboard'))

    sent = 0
    students = Student.query.all()
    for student in students:
        recent_records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).limit(3).all()
        if not (len(recent_records) == 3 and all(record.status == 'Absent' for record in recent_records)):
            continue

        parent = User.query.filter_by(student_id=student.id, role='parent').first()
        if not parent:
            continue

        msg = Message(
            sender_id=current_user.id,
            receiver_id=parent.id,
            content=(
                f"Dear Parent of {student.first_name} {student.last_name}, we have recorded three consecutive days of absence. "
                f"Please contact Pebbles College to confirm your child is safe and discuss immediate attendance support."
            )
        )
        db.session.add(msg)

        intervention = AttendanceIntervention(
            student_id=student.id,
            actor_id=current_user.id,
            action='Reminder Sent',
            note='Bulk attendance risk reminder sent to parent from dashboard.',
            resolved=False
        )
        db.session.add(intervention)
        sent += 1

    db.session.commit()
    flash(f"Attendance risk alert sent to {sent} parent(s).", "success")
    return redirect(url_for('dashboard'))


@app.route('/attendance/log-call', methods=['POST'])
@login_required
def log_attendance_call():
    if current_user.role not in ['admin', 'accountant']:
        return redirect(url_for('dashboard'))

    student_id = request.form.get('student_id')
    note = (request.form.get('note') or '').strip()
    expected_return = request.form.get('expected_return_date')
    meeting_date_str = request.form.get('meeting_date')
    action_type = request.form.get('action_type', 'call')
    resolved = request.form.get('resolved') == 'on'

    if not student_id or not note:
        flash('Call note is required before saving intervention.', 'danger')
        return redirect(url_for('dashboard'))

    expected_return_date = None
    if expected_return:
        try:
            expected_return_date = datetime.strptime(expected_return, '%Y-%m-%d').date()
        except ValueError:
            flash('Expected return date format is invalid.', 'danger')
            return redirect(url_for('dashboard'))

    meeting_date = None
    if meeting_date_str:
        try:
            meeting_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Meeting date format is invalid.', 'danger')
            return redirect(url_for('dashboard'))

    if action_type == 'meeting' and not meeting_date:
        flash('Meeting date is required to schedule a meeting.', 'danger')
        return redirect(url_for('dashboard'))

    if action_type == 'meeting':
        action_value = 'Meeting Scheduled'
    elif resolved:
        action_value = 'Resolved'
    else:
        action_value = 'Call Logged'

    intervention = AttendanceIntervention(
        student_id=student_id,
        actor_id=current_user.id,
        action=action_value,
        note=note,
        expected_return_date=expected_return_date,
        meeting_date=meeting_date,
        resolved=resolved
    )
    db.session.add(intervention)
    db.session.commit()

    flash('Attendance intervention logged successfully.', 'success')
    return redirect(url_for('dashboard'))


# --- FINANCE INTELLIGENCE ENGINE ---
@app.route('/finance-intelligence')
@login_required
def finance_intelligence():
    if current_user.role not in ['admin', 'accountant']:
        return redirect(url_for('dashboard'))

    import sqlalchemy as sa

    total_expected = db.session.query(sa.func.sum(Student.tuition_fee)).scalar() or 0
    total_collected = db.session.query(sa.func.sum(Income.amount)).scalar() or 0

    deficit = total_expected - total_collected
    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

    if collection_rate < 50:
        insight = "Critical: Less than half of fees collected. Recommend immediate SMS blast to Grade 7 & 9 parents."
        insight_color = "#ef4444"
        bar_color = "#ef4444"
    elif collection_rate < 85:
        insight = "Stable: Collection is on track, but some fees remain outstanding. Projected full collection by month-end if reminders continue."
        insight_color = "#f59e0b"
        bar_color = "#f59e0b"
    else:
        insight = "Excellent: Budget surplus likely. Good time to approve pending maintenance requests."
        insight_color = "#10b981"
        bar_color = "#10b981"

    return render_template('admin/finance_ai.html',
                           expected=total_expected,
                           collected=total_collected,
                           deficit=deficit,
                           rate=round(collection_rate, 1),
                           insight=insight,
                           insight_color=insight_color,
                           bar_color=bar_color)


@app.route('/reports/monthly-summary')
@login_required
def download_monthly_report():
    if current_user.role not in ['admin', 'accountant']:
        return redirect(url_for('dashboard'))

    now = datetime.utcnow()
    month_start, next_month = month_window(now)
    month_label = now.strftime('%B %Y')

    settings = SchoolSettings.query.first() or SchoolSettings()

    total_expected = db.session.query(db.func.sum(Student.tuition_fee)).scalar() or 0
    total_collected = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= month_start,
        Income.date < next_month
    ).scalar() or 0
    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

    month_payroll_records = PayrollRecord.query.filter(
        PayrollRecord.period_year == now.year,
        PayrollRecord.period_month == now.month
    ).all()
    payroll_total = sum(record.net_salary or 0 for record in month_payroll_records)

    inventory_items = Inventory.query.all()
    total_asset_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in inventory_items)
    total_units = sum(item.quantity or 0 for item in inventory_items)
    damaged_units = sum((item.quantity or 0) for item in inventory_items if (item.condition or 'Good') == 'Damaged')
    lost_units = sum((item.quantity or 0) for item in inventory_items if (item.condition or 'Good') == 'Lost')
    risk_units = damaged_units + lost_units
    risk_percent = (risk_units / total_units * 100) if total_units > 0 else 0
    damaged_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in inventory_items if (item.condition or 'Good') == 'Damaged')
    lost_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in inventory_items if (item.condition or 'Good') == 'Lost')
    risk_value = damaged_value + lost_value

    payroll_ratio = (payroll_total / total_collected * 100) if total_collected > 0 else 0

    if collection_rate >= 80 and payroll_ratio < 60 and risk_percent < 10:
        executive_summary = (
            f'{month_label} was a strong month with {collection_rate:.1f}% fee collection. '
            f'Payroll remained controlled at {payroll_ratio:.1f}% of collected fees, and '
            f'asset risk stayed low at {risk_percent:.1f}%. '
            f'The school is in a stable operational position.'
        )
    elif collection_rate < 60:
        executive_summary = (
            f'{month_label} requires urgent intervention: fee collection closed at {collection_rate:.1f}%, '
            f'while payroll consumed {payroll_ratio:.1f}% of collected fees. '
            f'Immediate parent reminder campaigns and spending controls are recommended.'
        )
    else:
        executive_summary = (
            f'{month_label} showed mixed performance with {collection_rate:.1f}% fee collection and '
            f'payroll at {payroll_ratio:.1f}% of collected fees. '
            f'Asset risk stands at {risk_percent:.1f}% and should be monitored closely next month.'
        )

    upcoming_exams = SchoolEvent.query.filter(
        SchoolEvent.category == 'Exam',
        SchoolEvent.start_date >= now
    ).order_by(SchoolEvent.start_date.asc()).limit(5).all()

    report_stream = BytesIO()
    document = SimpleDocTemplate(
        report_stream,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f'{settings.school_name} Monthly Financial Summary'
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#475569'),
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=6,
    )

    story = []

    logo_path = os.path.join(app.static_folder, 'uploads', settings.school_logo or '')
    if settings.school_logo and os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 1.8 * cm
        logo.drawWidth = 1.8 * cm
        story.append(logo)
        story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph(settings.school_name or 'Pebbles College', title_style))
    story.append(Paragraph(f'Monthly Financial Summary - {month_label}', subtitle_style))
    story.append(Paragraph(f'Report generated on {now.strftime("%d %B %Y %H:%M UTC")}', subtitle_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph('Executive Summary', section_style))
    story.append(Paragraph(executive_summary, styles['BodyText']))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph('Revenue vs Expense Snapshot', section_style))
    finance_table = Table([
        ['Metric', 'Value (K)'],
        ['Total Fees Collected (This Month)', f'{total_collected:,.2f}'],
        ['Total Payroll Paid (This Month)', f'{payroll_total:,.2f}'],
        ['Payroll as % of Collected Fees', f'{payroll_ratio:.1f}%'],
        ['Expected Fees (Portfolio)', f'{total_expected:,.2f}'],
        ['Collection Rate', f'{collection_rate:.1f}%'],
    ], colWidths=[10 * cm, 6.5 * cm])
    finance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(finance_table)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph('Asset Health Snapshot', section_style))
    inventory_table = Table([
        ['Metric', 'Value'],
        ['Total Inventory Value', f'K {total_asset_value:,.2f}'],
        ['Damaged Units', str(damaged_units)],
        ['Lost Units', str(lost_units)],
        ['Damaged + Lost %', f'{risk_percent:.1f}%'],
        ['Damaged + Lost Value', f'K {risk_value:,.2f}'],
    ], colWidths=[10 * cm, 6.5 * cm])
    inventory_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdfa')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f0fdfa')]),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(inventory_table)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph('Forward-Looking (Upcoming Exams)', section_style))
    if upcoming_exams:
        for exam in upcoming_exams:
            days_left = (exam.start_date.date() - now.date()).days
            exam_line = (
                f'<b>{exam.title}</b> - {exam.start_date.strftime("%d %b %Y")}'
                f' ({days_left} days away)'
            )
            if exam.description:
                exam_line += f' - {exam.description}'
            story.append(Paragraph(exam_line, styles['BodyText']))
            story.append(Spacer(1, 0.08 * cm))
    else:
        story.append(Paragraph('No upcoming exams are currently scheduled.', styles['BodyText']))

    document.build(story)
    report_stream.seek(0)

    filename = f'Board_Report_{now.strftime("%Y_%m")}.pdf'
    return send_file(
        report_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# --- INVENTORY & ASSET TRACKING ---
@app.route('/finance/inventory')
@login_required
def inventory_hub():
    items = Inventory.query.all()

    total_units = sum(item.quantity or 0 for item in items)
    total_asset_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in items)

    damaged_items = [item for item in items if (item.condition or 'Good') == 'Damaged']
    lost_items = [item for item in items if (item.condition or 'Good') == 'Lost']
    damaged_units = sum(item.quantity or 0 for item in damaged_items)
    lost_units = sum(item.quantity or 0 for item in lost_items)

    damaged_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in damaged_items)
    lost_value = sum((item.quantity or 0) * (item.unit_value or 0) for item in lost_items)
    estimated_repair_cost = round(damaged_value * 0.35, 2)

    tablet_items = [
        item for item in items
        if 'tablet' in (item.name or '').lower() or (item.category or '').lower() == 'electronics'
    ]
    total_tablet_units = sum(item.quantity or 0 for item in tablet_items)
    damaged_tablet_units = sum((item.quantity or 0) for item in tablet_items if (item.condition or 'Good') == 'Damaged')
    damaged_tablet_percent = round((damaged_tablet_units / total_tablet_units) * 100, 1) if total_tablet_units else 0

    if damaged_tablet_percent >= 12:
        inventory_insight = (
            f'Asset Alert: {damaged_tablet_percent}% of tablets are marked Damaged. '
            f'Estimated repair cost: K{estimated_repair_cost:,.2f}.'
        )
        insight_tone = 'critical'
    elif (lost_units + damaged_units) > 0:
        affected = damaged_units + lost_units
        risk_percent = round((affected / total_units) * 100, 1) if total_units else 0
        inventory_insight = (
            f'Inventory Watch: {risk_percent}% of tracked assets are Damaged or Lost. '
            f'Escalate procurement review this week.'
        )
        insight_tone = 'watch'
    else:
        inventory_insight = 'Inventory health is stable. No damaged or lost assets are currently flagged.'
        insight_tone = 'healthy'

    return render_template(
        'finance/inventory.html',
        items=items,
        total_units=total_units,
        total_asset_value=round(total_asset_value, 2),
        damaged_units=damaged_units,
        lost_units=lost_units,
        damaged_value=round(damaged_value, 2),
        lost_value=round(lost_value, 2),
        estimated_repair_cost=estimated_repair_cost,
        damaged_tablet_percent=damaged_tablet_percent,
        inventory_insight=inventory_insight,
        insight_tone=insight_tone
    )

@app.route('/finance/inventory/add', methods=['POST'])
@login_required
def add_inventory():
    quantity = request.form.get('quantity') or 1
    unit_value = request.form.get('unit_value') or 0
    new_item = Inventory(
        name=request.form.get('name'),
        category=request.form.get('category'),
        quantity=quantity,
        condition=request.form.get('condition') or 'Good',
        unit_value=unit_value
    )
    db.session.add(new_item)
    db.session.commit()
    flash("Item added to school assets!", "success")
    return redirect(url_for('inventory_hub'))


@app.route('/finance/inventory/<int:item_id>/condition', methods=['POST'])
@login_required
def update_inventory_condition(item_id):
    item = Inventory.query.get_or_404(item_id)
    condition = (request.form.get('condition') or 'Good').strip()
    if condition not in ['New', 'Good', 'Damaged', 'Lost']:
        flash('Invalid condition selected.', 'danger')
        return redirect(url_for('inventory_hub'))

    item.condition = condition
    db.session.commit()
    flash(f'Condition updated for {item.name}.', 'success')
    return redirect(url_for('inventory_hub'))



@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- STAFF CHAT ROUTES ---
@app.route('/staff-chat', endpoint='staff_chat_page')
@login_required
def staff_chat_page():
    from models import User
    staff_members = User.query.filter(User.role != 'parent', User.id != current_user.id).all()
    return render_template('admin/staff_chat.html', staff=staff_members)

@app.route('/chat/with/<int:user_id>')
@login_required
def private_chat(user_id):
    from models import User, Message
    recipient = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    return render_template('admin/private_chat.html', recipient=recipient, messages=messages)


# ------------------- CALENDAR ROUTES -------------------
@app.route('/calendar')
@login_required
def school_calendar():
    """Display the school calendar with events."""
    events = SchoolEvent.query.order_by(SchoolEvent.start_date).all()
    return render_template('admin/calendar.html', events=events)


@app.route('/calendar/api/events')
@login_required
def calendar_events_api():
    """API endpoint for FullCalendar.js to fetch events as JSON."""
    events = SchoolEvent.query.order_by(SchoolEvent.start_date).all()
    event_list = []
    for event in events:
        event_dict = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'description': event.description or '',
            'category': event.category or 'Academic'
        }
        if event.end_date:
            event_dict['end'] = event.end_date.isoformat()
        
        # Color coding by category
        if event.category == 'Holiday':
            event_dict['color'] = '#ef4444'  # Red
        elif event.category == 'Exam':
            event_dict['color'] = '#f59e0b'  # Amber
        elif event.category == 'Sport':
            event_dict['color'] = '#10b981'  # Green
        else:
            event_dict['color'] = '#3b82f6'  # Blue

        event_list.append(event_dict)
    
    return jsonify(event_list)


@app.route('/event/<int:event_id>/rsvp', methods=['POST'])
@login_required
def rsvp_event(event_id):
    """Handle RSVP/attendance for school events."""
    event = SchoolEvent.query.get_or_404(event_id)
    rsvp_status = request.form.get('rsvp_status', 'attending')  # attending, not_attending, maybe
    notes = request.form.get('notes', '')
    
    # Check if already RSVPed
    existing = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    if existing:
        existing.rsvp_status = rsvp_status
        existing.notes = notes
        existing.updated_at = datetime.utcnow()
    else:
        # If parent, link their student
        student_id = None
        if hasattr(current_user, 'role') and current_user.role == 'parent':
            student_id = current_user.student_id
        
        attendance = EventAttendance(
            event_id=event_id,
            user_id=current_user.id,
            student_id=student_id,
            rsvp_status=rsvp_status,
            notes=notes
        )
        db.session.add(attendance)
    
    db.session.commit()
    flash(f'RSVP updated: {rsvp_status.replace("_", " ").title()}', 'success')
    return redirect(request.referrer or url_for('school_calendar'))


@app.route('/event/<int:event_id>/rsvp-status')
@login_required
def get_rsvp_status(event_id):
    """Get current user's RSVP status for an event (JSON)."""
    attendance = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    if attendance:
        return jsonify({
            'rsvp_status': attendance.rsvp_status,
            'rsvp_count': EventAttendance.query.filter(
                EventAttendance.event_id == event_id,
                EventAttendance.rsvp_status == 'attending'
            ).count()
        })
    else:
        return jsonify({
            'rsvp_status': 'pending',
            'rsvp_count': EventAttendance.query.filter(
                EventAttendance.event_id == event_id,
                EventAttendance.rsvp_status == 'attending'
            ).count()
        })


# ------------------- RUN APP -------------------
if __name__ == '__main__':
    with app.app_context():
        ensure_database_schema()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', password=generate_password_hash('pebbles123'), role='admin')
            db.session.add(admin)
            db.session.commit()
        elif admin.role != 'admin':
            admin.role = 'admin'
            db.session.commit()
    app.run(debug=True)
