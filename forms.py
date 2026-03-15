from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from datetime import date
from models import User, Patient, Doctor
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional
from datetime import datetime, date

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class PatientForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()], format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    contact_number = StringField('Contact Number', validators=[Optional(), Length(min=10, max=15)])
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Add Patient')
    
    def validate_date_of_birth(self, field):
        if field.data > date.today():
            raise ValidationError('Date of birth cannot be in the future.')
        if field.data < date(1900, 1, 1):
            raise ValidationError('Please enter a valid date of birth.')

class EditPatientForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()], format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    contact_number = StringField('Contact Number', validators=[Optional(), Length(min=10, max=15)])
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Update Patient')
    
    def validate_date_of_birth(self, field):
        if field.data > date.today():
            raise ValidationError('Date of birth cannot be in the future.')
        if field.data < date(1900, 1, 1):
            raise ValidationError('Please enter a valid date of birth.')

class DoctorForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    specialization = StringField('Specialization', validators=[DataRequired(), Length(min=2, max=100)])
    contact_number = StringField('Contact Number', validators=[Optional(), Length(min=10, max=15)])
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Add Doctor')

class EditDoctorForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    specialization = StringField('Specialization', validators=[DataRequired(), Length(min=2, max=100)])
    contact_number = StringField('Contact Number', validators=[Optional(), Length(min=10, max=15)])
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Update Doctor')

class AppointmentForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    appointment_date = DateField('Appointment Date', validators=[DataRequired()], format='%Y-%m-%d')
    # Change appointment_time to StringField since we're dynamically populating it
    appointment_time = StringField('Appointment Time', validators=[DataRequired()])
    duration = SelectField('Duration', choices=[
        (30, '30 minutes'),
        (60, '1 hour'),
        (90, '1.5 hours'),
        (120, '2 hours')
    ], default=60, coerce=int, validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis/Reason', validators=[DataRequired()])
    submit = SubmitField('Schedule Appointment')
    
    def validate_appointment_date(self, field):
        if field.data < date.today():
            raise ValidationError('Appointment date cannot be in the past.')

class EditAppointmentForm(FlaskForm):
    # Remove the choices=[] from these fields
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    appointment_date = DateField('Appointment Date', validators=[DataRequired()], format='%Y-%m-%d')
    appointment_time = SelectField('Appointment Time', validators=[DataRequired()], validate_choice=False)
    duration = SelectField('Duration', choices=[
        (30, '30 minutes'),
        (60, '1 hour'),
        (90, '1.5 hours'),
        (120, '2 hours')
    ], coerce=int, validators=[DataRequired()])
    diagnosis = TextAreaField('Diagnosis/Reason', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Scheduled', 'Scheduled'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], validators=[DataRequired()])
    submit = SubmitField('Update Appointment')
    
    def validate_appointment_date(self, field):
        if field.data < date.today():
            raise ValidationError('Appointment date cannot be in the past.')
        

# Medical Record Upload Form
class MedicalRecordForm(FlaskForm):
    record_type = SelectField('Record Type', choices=[
        ('Lab Report', 'Lab Report'),
        ('X-Ray', 'X-Ray'),
        ('MRI', 'MRI'),
        ('CT Scan', 'CT Scan'),
        ('Prescription', 'Prescription'),
        ('Medical Certificate', 'Medical Certificate'),
        ('Discharge Summary', 'Discharge Summary'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    file = FileField('Medical Record File', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'], 'Only documents and images allowed!')
    ])
    submit = SubmitField('Upload Record')

# Prescription Form
class PrescriptionForm(FlaskForm):
    medication_name = StringField('Medication Name', validators=[DataRequired()])
    dosage = StringField('Dosage', validators=[DataRequired()])
    frequency = SelectField('Frequency', choices=[
        ('Once daily', 'Once daily'),
        ('Twice daily', 'Twice daily'),
        ('Three times daily', 'Three times daily'),
        ('Four times daily', 'Four times daily'),
        ('As needed', 'As needed'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    duration = StringField('Duration', validators=[DataRequired()])
    instructions = TextAreaField('Instructions', validators=[Optional()])
    submit = SubmitField('Add Prescription')