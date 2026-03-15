from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from sqlalchemy import text, func
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta

app = Flask(__name__)

# Get the path to the current folder
basedir = os.path.abspath(os.path.dirname(__file__))

# Point to the single, permanent database on disk
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'static/storage/nandulu_production.db')
app.config['UPLOAD_FOLDER'] = 'static/storage/uploads'
app.config['PROFILE_FOLDER'] = 'static/storage/profile_pics'

# Ensure the folders exist locally for testing
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROFILE_FOLDER'], exist_ok=True)

app.config['SECRET_KEY'] = 'change-this-to-a-strong-random-secret-key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column('name', db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    nrc_number = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='New Lead')
    notes = db.Column(db.Text)
    nrc_file = db.Column(db.String(200))
    payslip_file = db.Column(db.String(200))
    bank_statement_file = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref='leads')
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def name(self):
        return self.client_name

    @name.setter
    def name(self, value):
        self.client_name = value

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_goal = db.Column(db.Float, default=100000.0)
    company_name = db.Column(db.String(100), default="Purple Worth Studios")

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
    # New Staff Profile Fields
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    dob = db.Column(db.Date)
    role = db.Column(db.String(50), default='Agent')  # Options: Admin, Manager, Agent
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

    if 'user_id' not in lead_columns:
        db.session.execute(text("ALTER TABLE lead ADD COLUMN user_id INTEGER"))
        admin_user = User.query.filter_by(username='admin').first() or User.query.first()
        if admin_user:
            db.session.execute(text("UPDATE lead SET user_id = :admin_id WHERE user_id IS NULL"), {"admin_id": admin_user.id})
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
    # 1. Get settings with a fallback
    app_settings = Settings.query.first()

    # If settings don't exist yet, use 50000 as a default
    monthly_target = (
        app_settings.target_amount
        if app_settings and getattr(app_settings, 'target_amount', None)
        else 50000
    )

    # 2. Get leads based on role
    if current_user.role in ['Admin', 'Manager']:
        leads = Lead.query.all()
    else:
        leads = Lead.query.filter_by(user_id=current_user.id).all()

    # 2. Ensure total_revenue is always a number
    closed_leads = [l for l in leads if l.status == 'Closed Deal']
    total_revenue = sum(l.amount for l in closed_leads if l.amount) or 0

    # 3. Calculate percentage safely
    percentage = (total_revenue / max(monthly_target, 1)) * 100

    stats = {
        'total': len(leads),
        'contacted': len([l for l in leads if l.status == 'Contacted']),
        'negotiating': len([l for l in leads if l.status == 'Negotiation']),
        'closed': len(closed_leads),
        'revenue_val': total_revenue,
        'target_val': monthly_target,
        'target_percent': min(percentage, 100)
    }

    return render_template('dashboard.html', leads=leads, stats=stats, current_date=datetime.utcnow().date())

@app.route('/add', methods=['GET'])
@login_required
def add_page():
    return render_template('add.html')

# Accepts both the new POST /add flow and legacy /save_lead form action.
@app.route('/add', methods=['POST'])
@app.route('/save_lead', methods=['POST'])
@login_required
def add_lead():
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

    client_name = request.form.get('client_name') or request.form.get('name')
    if not client_name:
        flash("Client name is required.", "danger")
        return redirect(url_for('add_page'))

    new_lead = Lead(
        client_name=client_name,
        phone=request.form.get('phone'),
        nrc_number=request.form.get('nrc_number'),
        amount=float(request.form.get('amount')),
        user_id=current_user.id,
        due_date=due_date,
        notes=request.form.get('notes'),
        nrc_file=save_file('nrc_file'),
        payslip_file=save_file('payslip_file'),
        bank_statement_file=save_file('bank_statement_file')
    )
    db.session.add(new_lead)
    db.session.commit()
    flash(f"Success! {client_name}'s application has been registered.", "success")
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
    lead.client_name = request.form.get('name')
    lead.phone = request.form.get('phone')
    lead.nrc_number = request.form.get('nrc_number')
    lead.amount = float(request.form.get('amount'))
    lead.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None
    lead.notes = request.form.get('notes')
    
    db.session.commit()
    flash(f"Profile for {lead.client_name} updated successfully!", "success")
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

@app.route('/create_staff', methods=['GET'])
@login_required
def create_staff():
    # Optional: Only let the 'admin' create other users
    if current_user.username != 'admin':
        flash("You don't have permission to create staff.", "danger")
        return redirect(url_for('dashboard'))

    return render_template('create_staff.html')


@app.route('/create_staff', methods=['POST'])
@login_required
def create_staff_post():
    if current_user.username != 'admin':
        flash("You don't have permission to create staff.", "danger")
        return redirect(url_for('dashboard'))

    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'Agent')

    if role not in ['Agent', 'Manager', 'Admin']:
        role = 'Agent'

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for('create_staff'))

    exists = User.query.filter_by(username=username).first()
    if exists:
        flash("Username already taken!", "danger")
        return redirect(url_for('create_staff'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    flash(f"Staff account for {username} created as {role}!", "success")
    return redirect(url_for('create_staff'))


@app.route('/admin/staff')
@login_required
def manage_staff():
    # Only allow the admin user to see this page.
    if current_user.username != 'admin':
        flash("Access denied: Admins only.", "danger")
        return redirect(url_for('dashboard'))

    all_staff = User.query.all()
    return render_template('manage_staff.html', staff_list=all_staff)


@app.route('/admin/staff/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_staff(user_id):
    if current_user.username != 'admin':
        flash("Access denied: Admins only.", "danger")
        return redirect(url_for('dashboard'))

    user_to_delete = User.query.get_or_404(user_id)

    # Prevent admin from deleting themselves.
    if user_to_delete.id == current_user.id:
        flash("You cannot delete your own admin account!", "warning")
    else:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"Staff member {user_to_delete.username} removed.", "success")

    return redirect(url_for('manage_staff'))




with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROFILE_FOLDER'], exist_ok=True)
    print("✅ Storage Vaults Verified & Ready")

if __name__ == '__main__':
    app.run(debug=True)