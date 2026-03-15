from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, date, timedelta, time
import os
from flask import render_template_string 
from werkzeug.utils import secure_filename
from forms import LoginForm, RegistrationForm, PatientForm, DoctorForm, AppointmentForm, EditPatientForm, EditDoctorForm, EditAppointmentForm, MedicalRecordForm, PrescriptionForm
from models import db, User, Patient, Doctor, Appointment, MedicalRecord, Prescription
from decorators import admin_required

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Add these configurations
app.config['UPLOAD_FOLDER'] = 'static/uploads/medical_records'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function to render templates with appropriate base template
def render_template_with_role(template, **context):
    """Helper function to render templates with appropriate base template"""
    if current_user.is_authenticated and current_user.role == 'admin':
        base_template = 'base_admin.html'
    else:
        base_template = 'base_user.html'
    
    return render_template(template, base_template=base_template, **context)

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data, 
            email=form.email.data, 
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=hashed_password,
            role='staff'  # Default role for new users
        )
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    # Get counts for dashboard
    patient_count = Patient.query.count()
    doctor_count = Doctor.query.count()
    appointment_count = Appointment.query.filter(
        Appointment.appointment_date >= date.today()
    ).count()
    user_count = User.query.count()  # Add this line
    
    # Get recent activities (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_activities = Appointment.query.filter(
        Appointment.created_at >= yesterday
    ).order_by(Appointment.created_at.desc()).all()
    
    # Use different templates based on role
    if current_user.role == 'admin':
        return render_template('admin_dashboard.html', 
                             title='Admin Dashboard',
                             patient_count=patient_count,
                             doctor_count=doctor_count,
                             appointment_count=appointment_count,
                             user_count=user_count,  # Add this line
                             recent_activities=recent_activities)
    else:
        return render_template('user_dashboard.html', 
                             title='Dashboard',
                             patient_count=patient_count,
                             doctor_count=doctor_count,
                             appointment_count=appointment_count,
                             recent_activities=recent_activities)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin-only routes
@app.route('/admin/users')
@login_required
@admin_required
def user_management():
    users = User.query.all()
    return render_template_with_role('admin_users.html', title='User Management', users=users)

@app.route('/admin/reports')
@login_required
@admin_required
def system_reports():
    # Get report data
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    total_appointments = Appointment.query.count()
    total_users = User.query.count()
    
    # Appointment statistics by status
    appointment_stats = db.session.query(
        Appointment.status,
        db.func.count(Appointment.id)
    ).group_by(Appointment.status).all()
    
    # Recent appointments (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_appointments = Appointment.query.filter(
        Appointment.created_at >= week_ago
    ).count()
    
    return render_template_with_role('admin_reports.html', 
                                   title='System Reports',
                                   total_patients=total_patients,
                                   total_doctors=total_doctors,
                                   total_appointments=total_appointments,
                                   total_users=total_users,
                                   appointment_stats=appointment_stats,
                                   recent_appointments=recent_appointments)

@app.route('/admin/audit-logs')
@login_required
@admin_required
def audit_logs():
    # For now, we'll show recent user activities
    # In a real system, you'd have a proper audit log table
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()
    
    return render_template_with_role('admin_audit_logs.html', 
                                   title='Audit Logs',
                                   recent_users=recent_users,
                                   recent_appointments=recent_appointments)

@app.route('/patients')
@login_required
def patients():
    search_query = request.args.get('search', '')
    if search_query:
        all_patients = Patient.query.filter(
            (Patient.first_name.ilike(f'%{search_query}%')) |
            (Patient.last_name.ilike(f'%{search_query}%')) |
            (Patient.contact_number.ilike(f'%{search_query}%')) |
            (Patient.email.ilike(f'%{search_query}%'))
        ).all()
    else:
        all_patients = Patient.query.all()
    return render_template_with_role('patients.html', title='Patients', patients=all_patients, search_query=search_query)

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        patient = Patient(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data,
            contact_number=form.contact_number.data,
            email=form.email.data
        )
        db.session.add(patient)
        db.session.commit()
        flash('Patient has been added successfully!', 'success')
        return redirect(url_for('patients'))
    return render_template_with_role('add_patient.html', title='Add Patient', form=form)

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = EditPatientForm(obj=patient)
    
    if form.validate_on_submit():
        patient.first_name = form.first_name.data
        patient.last_name = form.last_name.data
        patient.date_of_birth = form.date_of_birth.data
        patient.gender = form.gender.data
        patient.contact_number = form.contact_number.data
        patient.email = form.email.data
        
        db.session.commit()
        flash('Patient has been updated successfully!', 'success')
        return redirect(url_for('patients'))
    
    return render_template_with_role('edit_patient.html', title='Edit Patient', form=form, patient=patient)

@app.route('/view_patient/<int:patient_id>')
@login_required
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    return render_template_with_role('view_patient.html', title='View Patient', patient=patient, appointments=appointments)

@app.route('/delete_patient/<int:patient_id>')
@login_required
@admin_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Delete associated appointments first
    Appointment.query.filter_by(patient_id=patient_id).delete()
    
    db.session.delete(patient)
    db.session.commit()
    flash('Patient has been deleted successfully!', 'success')
    return redirect(url_for('patients'))

@app.route('/doctors')
@login_required
def doctors():
    search_query = request.args.get('search', '')
    if search_query:
        all_doctors = Doctor.query.filter(
            (Doctor.first_name.ilike(f'%{search_query}%')) |
            (Doctor.last_name.ilike(f'%{search_query}%')) |
            (Doctor.specialization.ilike(f'%{search_query}%')) |
            (Doctor.contact_number.ilike(f'%{search_query}%')) |
            (Doctor.email.ilike(f'%{search_query}%'))
        ).all()
    else:
        all_doctors = Doctor.query.all()
    return render_template_with_role('doctors.html', title='Doctors', doctors=all_doctors, search_query=search_query)

@app.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    form = DoctorForm()
    if form.validate_on_submit():
        doctor = Doctor(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            gender=form.gender.data,
            specialization=form.specialization.data,
            contact_number=form.contact_number.data,
            email=form.email.data
        )
        db.session.add(doctor)
        db.session.commit()
        flash('Doctor has been added successfully!', 'success')
        return redirect(url_for('doctors'))
    return render_template_with_role('add_doctor.html', title='Add Doctor', form=form)

@app.route('/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    form = EditDoctorForm(obj=doctor)
    
    if form.validate_on_submit():
        doctor.first_name = form.first_name.data
        doctor.last_name = form.last_name.data
        doctor.gender = form.gender.data
        doctor.specialization = form.specialization.data
        doctor.contact_number = form.contact_number.data
        doctor.email = form.email.data
        
        db.session.commit()
        flash('Doctor has been updated successfully!', 'success')
        return redirect(url_for('doctors'))
    
    return render_template_with_role('edit_doctor.html', title='Edit Doctor', form=form, doctor=doctor)

@app.route('/view_doctor/<int:doctor_id>')
@login_required
def view_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
    return render_template_with_role('view_doctor.html', title='View Doctor', doctor=doctor, appointments=appointments)

@app.route('/delete_doctor/<int:doctor_id>')
@login_required
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    # Delete associated appointments first
    Appointment.query.filter_by(doctor_id=doctor_id).delete()
    
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor has been deleted successfully!', 'success')
    return redirect(url_for('doctors'))

@app.route('/appointments')
@login_required
def appointments():
    search_query = request.args.get('search', '')
    if search_query:
        all_appointments = Appointment.query.join(Patient).join(Doctor).filter(
            (Patient.first_name.ilike(f'%{search_query}%')) |
            (Patient.last_name.ilike(f'%{search_query}%')) |
            (Doctor.first_name.ilike(f'%{search_query}%')) |
            (Doctor.last_name.ilike(f'%{search_query}%')) |
            (Appointment.diagnosis.ilike(f'%{search_query}%')) |
            (Appointment.status.ilike(f'%{search_query}%'))
        ).all()
    else:
        all_appointments = Appointment.query.all()
    return render_template_with_role('appointments.html', title='Appointments', appointments=all_appointments, search_query=search_query)

@app.route('/add_appointment', methods=['GET', 'POST'])
@login_required
def add_appointment():
    form = AppointmentForm()
    
    # Always update choices for patient and doctor
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    
    # Set choices for the form fields
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients] or [('', 'No patients available')]
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name} ({d.specialization})") for d in doctors] or [('', 'No doctors available')]
    form.appointment_time.choices = [('', 'Please select doctor and date first')]
    
    if form.validate_on_submit():
        # Parse the time string to time object
        appointment_time = datetime.strptime(form.appointment_time.data, "%H:%M").time()
        
        # Check for appointment conflicts
        existing_appointment = check_appointment_conflict(
            form.doctor_id.data,
            form.appointment_date.data,
            appointment_time,
            form.duration.data
        )
        
        if existing_appointment:
            flash('This time slot is no longer available. Please choose a different time.', 'danger')
            # Regenerate available slots
            available_slots = get_available_time_slots(
                form.doctor_id.data, 
                form.appointment_date.data, 
                form.duration.data
            )
            form.appointment_time.choices = [(slot, slot) for slot in available_slots] or [('', 'No available slots')]
            return render_template_with_role('add_appointment.html', title='Add Appointment', form=form)
        
        appointment = Appointment(
            patient_id=form.patient_id.data,
            doctor_id=form.doctor_id.data,
            appointment_date=form.appointment_date.data,
            appointment_time=appointment_time,
            duration=form.duration.data,
            diagnosis=form.diagnosis.data,
            status='Scheduled'
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment has been scheduled successfully!', 'success')
        return redirect(url_for('appointments'))
    
    return render_template_with_role('add_appointment.html', title='Add Appointment', form=form)

@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    form = EditAppointmentForm(obj=appointment)
    
    # Always set choices for patient and doctor
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    
    form.patient_id.choices = [(p.id, f"{p.first_name} {p.last_name}") for p in patients] or [('', 'No patients available')]
    form.doctor_id.choices = [(d.id, f"Dr. {d.first_name} {d.last_name} ({d.specialization})") for d in doctors] or [('', 'No doctors available')]
    
    # Convert time to string for the form
    form.appointment_time.data = appointment.appointment_time.strftime("%H:%M")
    
    if form.validate_on_submit():
        # Parse the time string to time object
        appointment_time = datetime.strptime(form.appointment_time.data, "%H:%M").time()
        
        # Check for appointment conflicts (excluding current appointment)
        existing_appointment = check_appointment_conflict(
            form.doctor_id.data,
            form.appointment_date.data,
            appointment_time,
            form.duration.data,
            appointment_id  # Exclude current appointment
        )
        
        if existing_appointment:
            flash('This time slot is no longer available. Please choose a different time.', 'danger')
            return render_template_with_role('edit_appointment.html', title='Edit Appointment', form=form, appointment=appointment)
        
        appointment.patient_id = form.patient_id.data
        appointment.doctor_id = form.doctor_id.data
        appointment.appointment_date = form.appointment_date.data
        appointment.appointment_time = appointment_time
        appointment.duration = form.duration.data
        appointment.diagnosis = form.diagnosis.data
        appointment.status = form.status.data
        
        db.session.commit()
        flash('Appointment has been updated successfully!', 'success')
        return redirect(url_for('appointments'))
    
    return render_template_with_role('edit_appointment.html', title='Edit Appointment', form=form, appointment=appointment)

def check_appointment_conflict(doctor_id, appointment_date, appointment_time, duration, exclude_appointment_id=None):
    """Check if there's a scheduling conflict for a doctor"""
    # Ensure duration is an integer
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        duration = 60  # Default to 60 minutes if conversion fails
    
    # Calculate end time
    start_datetime = datetime.combine(appointment_date, appointment_time)
    end_datetime = start_datetime + timedelta(minutes=duration)
    
    # Query for overlapping appointments
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == 'Scheduled'  # Only check scheduled appointments
    )
    
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)
    
    existing_appointments = query.all()
    
    for appointment in existing_appointments:
        appt_start = datetime.combine(appointment.appointment_date, appointment.appointment_time)
        appt_end = appt_start + timedelta(minutes=int(appointment.duration))  # Ensure int here
        
        # Check for overlap
        if (start_datetime < appt_end) and (end_datetime > appt_start):
            return appointment
    
    return None

@app.route('/view_appointment/<int:appointment_id>')
@login_required
def view_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template_with_role('view_appointment.html', title='View Appointment', appointment=appointment)

@app.route('/delete_appointment/<int:appointment_id>')
@login_required
@admin_required
def delete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment has been deleted successfully!', 'success')
    return redirect(url_for('appointments'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('dashboard'))
    
    # Search patients
    patients = Patient.query.filter(
        (Patient.first_name.ilike(f'%{query}%')) |
        (Patient.last_name.ilike(f'%{query}%')) |
        (Patient.contact_number.ilike(f'%{query}%')) |
        (Patient.email.ilike(f'%{query}%'))
    ).all()
    
    # Search doctors
    doctors = Doctor.query.filter(
        (Doctor.first_name.ilike(f'%{query}%')) |
        (Doctor.last_name.ilike(f'%{query}%')) |
        (Doctor.specialization.ilike(f'%{query}%')) |
        (Doctor.contact_number.ilike(f'%{query}%')) |
        (Doctor.email.ilike(f'%{query}%'))
    ).all()
    
    # Search appointments
    appointments = Appointment.query.join(Patient).join(Doctor).filter(
        (Patient.first_name.ilike(f'%{query}%')) |
        (Patient.last_name.ilike(f'%{query}%')) |
        (Doctor.first_name.ilike(f'%{query}%')) |
        (Doctor.last_name.ilike(f'%{query}%')) |
        (Appointment.diagnosis.ilike(f'%{query}%')) |
        (Appointment.status.ilike(f'%{query}%'))
    ).all()
    
    return render_template('search_results.html', title='Search Results', 
                         query=query, patients=patients, doctors=doctors, appointments=appointments)

def get_available_time_slots(doctor_id, appointment_date, duration=60):
    """Get available time slots for a doctor on a specific date"""
    print(f"=== DEBUG: get_available_time_slots called ===")
    print(f"Doctor ID: {doctor_id}")
    print(f"Date: {appointment_date}")
    print(f"Duration: {duration} (type: {type(duration)})")
    
    # Ensure duration is an integer
    try:
        duration = int(duration)
    except (ValueError, TypeError):
        duration = 60  # Default to 60 minutes if conversion fails
        print(f"WARNING: Duration conversion failed, using default: {duration}")
    
    print(f"Duration after conversion: {duration} (type: {type(duration)})")
    
    # Define working hours (9 AM to 5 PM)
    all_slots = []
    start = datetime.strptime("09:00", "%H:%M")
    end = datetime.strptime("17:00", "%H:%M")
    
    current = start
    while current <= end:
        all_slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=30)
    
    print(f"All possible slots: {all_slots}")
    
    # Get existing appointments for this doctor on this date
    existing_appointments = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        status='Scheduled'
    ).all()
    
    print(f"Found {len(existing_appointments)} existing appointments")
    
    # Convert to set for faster lookup
    booked_slots = set()
    
    for i, appointment in enumerate(existing_appointments):
        print(f"Appointment {i+1}: {appointment.appointment_time} for {appointment.duration} mins")
        # Calculate all time slots that would be occupied by this appointment
        start_time = appointment.appointment_time
        end_time = (datetime.combine(appointment_date, start_time) + 
                   timedelta(minutes=int(appointment.duration))).time()  # Ensure int here too
        
        current_time = datetime.combine(appointment_date, start_time)
        end_datetime = datetime.combine(appointment_date, end_time)
        
        while current_time < end_datetime:
            slot_str = current_time.strftime("%H:%M")
            booked_slots.add(slot_str)
            print(f"  Booking slot: {slot_str}")
            current_time += timedelta(minutes=30)
    
    print(f"Booked slots: {sorted(booked_slots)}")
    
    # Filter out booked slots and ensure enough time is available
    available_slots = []
    for slot in all_slots:
        slot_time = datetime.strptime(slot, "%H:%M").time()
        slot_end = (datetime.combine(appointment_date, slot_time) + timedelta(minutes=duration)).time()
        
        # Check if slot is available and doesn't extend past 17:00
        if slot not in booked_slots and slot_end <= time(17, 0):
            available_slots.append(slot)
    
    print(f"Available slots: {available_slots}")
    print("=== DEBUG: End ===")
    return available_slots

@app.context_processor
def inject_today_date():
    """Inject today's date into all templates"""
    return {'min_date': date.today().strftime('%Y-%m-%d')}

@app.route('/get_available_slots', methods=['POST'])
@login_required
def get_available_slots():
    try:
        # Get data from form
        doctor_id = request.form.get('doctor_id')
        appointment_date_str = request.form.get('appointment_date')
        duration = request.form.get('duration', 60, type=int)
        
        print(f"DEBUG get_available_slots:")
        print(f"  doctor_id: {doctor_id} (type: {type(doctor_id)})")
        print(f"  appointment_date: {appointment_date_str}")
        print(f"  duration: {duration} (type: {type(duration)})")
        
        if not doctor_id or not appointment_date_str:
            print("  ERROR: Missing doctor_id or appointment_date")
            return jsonify({'error': 'Doctor and date are required'}), 400
        
        appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
        available_slots = get_available_time_slots(int(doctor_id), appointment_date, duration)
        
        print(f"  Returning slots: {available_slots}")
        return jsonify({'slots': available_slots})
    except Exception as e:
        print(f"ERROR in get_available_slots: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data, 
            email=form.email.data, 
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=hashed_password,
            role='admin'  # Set role to admin
        )
        db.session.add(user)
        db.session.commit()
        flash('Admin account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register Admin', form=form)



@app.route('/create_admin')
def create_admin():
    # Check if admin already exists
    admin = User.query.filter_by(username='admin').first()
    if admin:
        flash('Admin user already exists!', 'warning')
        return redirect(url_for('login'))
    
    # Create admin user
    hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
    admin_user = User(
        username='admin',
        email='admin@hospital.com',
        first_name='System',
        last_name='Administrator',
        password=hashed_password,
        role='admin'
    )
    db.session.add(admin_user)
    db.session.commit()
    flash('Admin user created! Username: admin, Password: admin123', 'success')
    return redirect(url_for('login'))

@app.route('/check_user_roles')
def check_user_roles():
    users = User.query.all()
    result = []
    for user in users:
        result.append(f"ID: {user.id}, Username: {user.username}, Role: {user.role}")
    return "<br>".join(result)

@app.route('/make_admin/<username>')
def make_admin(username):
    user = User.query.filter_by(username=username).first()
    if user:
        user.role = 'admin'
        db.session.commit()
        return f"User {username} is now an admin!"
    return f"User {username} not found!"

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.role = request.form.get('role')
        db.session.commit()
        flash('User role updated successfully!', 'success')
        return redirect(url_for('user_management'))
    
    return render_template_with_role('edit_user.html', title='Edit User', user=user)

@app.route('/admin/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting own account
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('user_management'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/debug_slots')
def debug_slots():
    """Debug route to test if get_available_slots works"""
    # Test with some sample data
    test_doctor_id = 1  # Change this to an existing doctor ID in your system
    test_date = date.today()
    test_duration = 60
    
    available_slots = get_available_time_slots(test_doctor_id, test_date, test_duration)
    
    return jsonify({
        'test_doctor_id': test_doctor_id,
        'test_date': str(test_date),
        'test_duration': test_duration,
        'available_slots': available_slots
    })

# Configuration for file uploads
app.config['UPLOAD_FOLDER'] = 'static/uploads/medical_records'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Medical Records Routes
@app.route('/patient/<int:patient_id>/medical_records')
@login_required
def patient_medical_records(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    medical_records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.upload_date.desc()).all()
    return render_template_with_role('medical_records.html', title='Medical Records', 
                                   patient=patient, medical_records=medical_records)

@app.route('/patient/<int:patient_id>/upload_medical_record', methods=['GET', 'POST'])
@login_required
def upload_medical_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = MedicalRecordForm()
    
    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create unique filename to avoid conflicts
            unique_filename = f"{patient_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            medical_record = MedicalRecord(
                patient_id=patient_id,
                record_type=form.record_type.data,
                file_name=filename,
                file_path=unique_filename,
                description=form.description.data,
                uploaded_by=current_user.id
            )
            
            db.session.add(medical_record)
            db.session.commit()
            flash('Medical record uploaded successfully!', 'success')
            return redirect(url_for('patient_medical_records', patient_id=patient_id))
        else:
            flash('Invalid file type. Please upload PDF, image, or document files.', 'danger')
    
    return render_template_with_role('upload_medical_record.html', title='Upload Medical Record', 
                                   form=form, patient=patient)

@app.route('/delete_medical_record/<int:record_id>')
@login_required
@admin_required
def delete_medical_record(record_id):
    medical_record = MedicalRecord.query.get_or_404(record_id)
    
    # Delete the physical file
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], medical_record.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    db.session.delete(medical_record)
    db.session.commit()
    flash('Medical record deleted successfully!', 'success')
    return redirect(url_for('patient_medical_records', patient_id=medical_record.patient_id))

# Prescription Routes
@app.route('/patient/<int:patient_id>/prescriptions')
@login_required
def patient_prescriptions(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).order_by(Prescription.prescribed_date.desc()).all()
    return render_template_with_role('prescriptions.html', title='Prescriptions', 
                                   patient=patient, prescriptions=prescriptions)

@app.route('/patient/<int:patient_id>/add_prescription', methods=['GET', 'POST'])
@login_required
def add_prescription(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    form = PrescriptionForm()
    
    if form.validate_on_submit():
        prescription = Prescription(
            patient_id=patient_id,
            doctor_id=current_user.id if current_user.role == 'doctor' else 1,  # Default doctor or get from current user
            medication_name=form.medication_name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            duration=form.duration.data,
            instructions=form.instructions.data
        )
        
        db.session.add(prescription)
        db.session.commit()
        flash('Prescription added successfully!', 'success')
        return redirect(url_for('patient_prescriptions', patient_id=patient_id))
    
    return render_template_with_role('add_prescription.html', title='Add Prescription', 
                                   form=form, patient=patient)

@app.route('/prescription/<int:prescription_id>/toggle_status')
@login_required
def toggle_prescription_status(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    prescription.status = 'Completed' if prescription.status == 'Active' else 'Active'
    db.session.commit()
    flash(f'Prescription status updated to {prescription.status}', 'success')
    return redirect(url_for('patient_prescriptions', patient_id=prescription.patient_id))

@app.route('/delete_prescription/<int:prescription_id>')
@login_required
@admin_required
def delete_prescription(prescription_id):
    prescription = Prescription.query.get_or_404(prescription_id)
    patient_id = prescription.patient_id
    db.session.delete(prescription)
    db.session.commit()
    flash('Prescription deleted successfully!', 'success')
    return redirect(url_for('patient_prescriptions', patient_id=patient_id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", debug=True)