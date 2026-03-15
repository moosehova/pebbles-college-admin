from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///final_loan_crm.db'
app.config['UPLOAD_FOLDER'] = 'static/storage/uploads'
app.config['PROFILE_FOLDER'] = 'static/storage/profile_pics'

# Ensure the folders exist locally for testing
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROFILE_FOLDER'], exist_ok=True)

app.config['SECRET_KEY'] = 'change-this-to-a-strong-random-secret-key'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    nrc_number = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='New Lead')
    notes = db.Column(db.Text)
    nrc_file = db.Column(db.String(200))
    payslip_file = db.Column(db.String(200))
    bank_statement_file = db.Column(db.String(200))
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_goal = db.Column(db.Float, default=100000.0)
    company_name = db.Column(db.String(100), default="Purple Worth Studios")

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # New Staff Profile Fields
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    dob = db.Column(db.Date)
    role = db.Column(db.String(50), default="Loan Officer")
    profile_pic = db.Column(db.String(255), default='default_avatar.png')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

    # Lightweight schema sync for existing SQLite DBs without migrations.
    user_columns = [row[1] for row in db.session.execute(text("PRAGMA table_info(user)"))]
    if 'full_name' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN full_name VARCHAR(100)"))
    if 'email' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(100)"))
    if 'phone' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN phone VARCHAR(20)"))
    if 'dob' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN dob DATE"))
    if 'role' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(50)"))
        db.session.execute(text("UPDATE user SET role = 'Loan Officer' WHERE role IS NULL"))
    if 'profile_pic' not in user_columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN profile_pic VARCHAR(255)"))
        db.session.execute(text("UPDATE user SET profile_pic = 'default_avatar.png' WHERE profile_pic IS NULL"))
    db.session.commit()

    # Create first staff user if not exists
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('Nandulu2026', method='pbkdf2:sha256')
        admin = User(username='admin', password=hashed_pw)
        db.session.add(admin)
        db.session.commit()

    # Lightweight schema sync for existing SQLite DBs without migrations.
    lead_columns = [row[1] for row in db.session.execute(text("PRAGMA table_info(lead)"))]
    if 'updated_at' not in lead_columns:
        db.session.execute(text("ALTER TABLE lead ADD COLUMN updated_at DATETIME"))
        db.session.execute(text("UPDATE lead SET updated_at = created_at WHERE updated_at IS NULL"))
        db.session.commit()

    if 'due_date' not in lead_columns:
        db.session.execute(text("ALTER TABLE lead ADD COLUMN due_date DATE"))
        db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    # Get settings or create default if none exist
    settings = Settings.query.first()
    if not settings:
        settings = Settings(monthly_goal=100000.0)
        db.session.add(settings)
        db.session.commit()

    leads = Lead.query.all()
    revenue = sum(l.amount for l in leads if l.status == 'Closed Deal')
    
    # Use the goal from database instead of a hardcoded number
    goal = settings.monthly_goal
    percent = (revenue / goal * 100) if goal > 0 else 0

    # ... keep your other counts (total, contacted, etc.) ...
    total = len(leads)
    contacted_count = Lead.query.filter_by(status='Contacted').count()
    negot_count = Lead.query.filter_by(status='Negotiation').count()
    closed_deals = Lead.query.filter_by(status='Closed Deal').count()
    
    return render_template('dashboard.html', 
                           leads=leads, 
                           revenue=revenue,
                           monthly_goal=goal,
                           goal_percentage=round(percent, 1),
                           display_percent=min(percent, 100),
                           current_date=datetime.utcnow().date(),
                           total=total,
                           contacted_count=contacted_count,
                           negot_count=negot_count,
                           closed_deals=closed_deals)

@app.route('/add', methods=['GET', 'POST'])
def add_page():
    if request.method == 'POST':
        name = request.form['name']
        amount = float(request.form['amount'])
        lead = Lead(name=name, amount=amount)
        db.session.add(lead)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add.html')

# Update your save route to catch the notes
@app.route('/save_lead', methods=['POST'])
def save_lead():
    # 1. Handle File Uploads
    def save_file(field_name):
        file = request.files.get(field_name)
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return filename
        return None

    due_date_raw = request.form.get('due_date')
    due_date = datetime.strptime(due_date_raw, '%Y-%m-%d').date() if due_date_raw else None

    new_lead = Lead(
        name=request.form.get('name'),
        phone=request.form.get('phone'),
        nrc_number=request.form.get('nrc_number'),
        amount=float(request.form.get('amount')),
        due_date=due_date,
        notes=request.form.get('notes'),
        nrc_file=save_file('nrc_file'),
        payslip_file=save_file('payslip_file'),
        bank_statement_file=save_file('bank_statement_file')
    )
    db.session.add(new_lead)
    db.session.commit()
    flash(f"Success! {request.form.get('name')}'s application has been registered.", "success")
    return redirect(url_for('dashboard'))

@app.route('/update_status/<int:id>/<string:new_status>')
def update_status(id, new_status):
    lead = Lead.query.get_or_404(id)
    
    # Mapping the slug to the Display Name
    status_map = {
        'contacted': 'Contacted',
        'negotiation': 'Negotiation',
        'closed': 'Closed Deal'
    }
    
    if new_status in status_map:
        lead.status = status_map[new_status]
        db.session.commit()
        return "Success", 200

    return "Invalid Status", 400

@app.route('/profile/<int:id>')
def view_profile(id):
    lead = Lead.query.get_or_404(id)
    return render_template('profile.html', lead=lead)

@app.route('/update_lead/<int:id>', methods=['POST'])
def update_lead(id):
    lead = Lead.query.get_or_404(id)
    
    # Update the fields with the new data from the form
    lead.name = request.form.get('name')
    lead.phone = request.form.get('phone')
    lead.nrc_number = request.form.get('nrc_number')
    lead.amount = float(request.form.get('amount'))
    lead.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None
    lead.notes = request.form.get('notes')
    
    db.session.commit()
    flash(f"Profile for {lead.name} updated successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_lead/<int:id>')
def delete_lead(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted successfully.', 'warning')
    return redirect(url_for('dashboard'))

@app.route('/documents')
def documents_page():
    leads = Lead.query.all()
    return render_template('documents.html', leads=leads)

@app.route('/settings')
def settings_page():
    settings = Settings.query.first()
    if not settings:
        settings = Settings(monthly_goal=100000.0)
        db.session.add(settings)
        db.session.commit()
    return render_template('settings.html', settings=settings)

@app.route('/save_settings', methods=['POST'])
def save_settings():
    settings = Settings.query.first()
    settings.monthly_goal = float(request.form.get('monthly_goal'))
    settings.company_name = request.form.get('company_name')
    db.session.commit()
    return redirect(url_for('settings_page'))

@app.route('/staff/profile')
@login_required
def staff_profile_page():
    return render_template('staff_profile.html')

@app.route('/staff/profile/update', methods=['POST'])
@login_required
def update_staff_profile():
    # Handle File Upload
    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file.filename != '':
            filename = secure_filename(f"user_{current_user.id}_{file.filename}")
            file.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
            current_user.profile_pic = filename

    # Update other fields
    current_user.full_name = request.form.get('full_name')
    current_user.email = request.form.get('email')

    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('staff_profile_page'))

@app.route('/reports/upcoming')
@login_required
def upcoming_report():
    today = date.today()
    # Looking at the next 7 days for the summary
    next_week = today + timedelta(days=7)

    upcoming_loans = Lead.query.filter(Lead.due_date != None).order_by(Lead.due_date.asc()).all()

    # Calculate total expected from all upcoming loans
    total_expected = sum(lead.amount for lead in upcoming_loans if lead.status != 'Closed Deal')

    # Calculate how much is specifically due within the next 7 days
    due_this_week = sum(lead.amount for lead in upcoming_loans if today <= lead.due_date <= next_week)

    return render_template('upcoming_report.html',
                           leads=upcoming_loans,
                           today=today,
                           total_expected=total_expected,
                           due_this_week=due_this_week)

@app.route('/create_staff', methods=['GET', 'POST'])
@login_required
def create_staff():
    # Optional: Only let the 'admin' create other users
    if current_user.username != 'admin':
        flash("You don't have permission to create staff.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = request.form.get('username')
        passw = request.form.get('password')

        # Check if user already exists
        exists = User.query.filter_by(username=user).first()
        if exists:
            flash("Username already taken!", "danger")
        else:
            # HASH the password before saving
            hashed_password = generate_password_hash(passw, method='pbkdf2:sha256')
            new_user = User(username=user, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash(f"Staff account for {user} created!", "success")

    return render_template('create_staff.html')




if __name__ == '__main__':
    app.run(debug=True)