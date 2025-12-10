from extensions import db
from models import User, Department, Doctor, Patient, DoctorAvailability, Appointment
from functools import wraps
from flask_login import current_user
from flask import abort
from datetime import datetime, timedelta, time

# Setup function for initial data
def create_admin():
    """Create admin user if it doesn't exist"""
    # Check if admin already exists 
    existingAdmin = User.query.filter_by(username='admin').first()
    if existingAdmin is None:
        newAdmin = User(
            username='admin',
            email='admin@hospital.com',
            role='admin'
        )
        # Set password 
        newAdmin.set_password('admin123')  # Change this in production
    
        db.session.add(newAdmin)
        db.session.commit()
        print("Admin user created successfully!")
    
    # default departments 
    departmentsList = {
        'Cardiology': 'Heart and cardiovascular system',
        'Neurology': 'Brain and nervous system',
        'Orthopedics': 'Bones, joints, and muscles',
        'Pediatrics': 'Children health care',
        'Dermatology': 'Skin, hair, and nails',
        'General Medicine': 'General health and common diseases',
        'ENT': 'Ear, Nose, and Throat',
        'Ophthalmology': 'Eye care and vision',
    }
    
    
    for deptName, deptDescription in departmentsList.items():
        
        existingDept = Department.query.filter_by(name=deptName).first()
        
        if existingDept is None:
            # Create new department
            newDept = Department(name=deptName, description=deptDescription)
            db.session.add(newDept)
    
    db.session.commit()
    
    create_sample_data()


def create_sample_data():
    """Create sample doctors and patients for testing"""
    existingDoctors = Doctor.query.count()
    if existingDoctors > 0:
        return  # Data already exists
    
    # Sample doctors data
    sampleDoctors = [
        {'username': 'dr.smith', 'email': 'dr.smith@hospital.com', 'password': 'doctor123',
        'full_name': 'Dr. John Smith', 'specialization': 'Cardiologist', 'department': 'Cardiology',
        'phone': '9876543210', 'qualification': 'MBBS, MD Cardiology', 'experience': 15, 'fee': 500.0},
        
        {'username': 'dr.patel', 'email': 'dr.patel@hospital.com', 'password': 'doctor123',
        'full_name': 'Dr. Priya Patel', 'specialization': 'Neurologist', 'department': 'Neurology',
        'phone': '9876543211', 'qualification': 'MBBS, MD Neurology', 'experience': 12, 'fee': 600.0},
        
        {'username': 'dr.kumar', 'email': 'dr.kumar@hospital.com', 'password': 'doctor123',
        'full_name': 'Dr. Raj Kumar', 'specialization': 'Orthopedic Surgeon', 'department': 'Orthopedics',
        'phone': '9876543212', 'qualification': 'MBBS, MS Orthopedics', 'experience': 10, 'fee': 450.0},
        
        {'username': 'dr.sharma', 'email': 'dr.sharma@hospital.com', 'password': 'doctor123',
        'full_name': 'Dr. Anjali Sharma', 'specialization': 'Pediatrician', 'department': 'Pediatrics',
        'phone': '9876543213', 'qualification': 'MBBS, MD Pediatrics', 'experience': 8, 'fee': 400.0},
        
        {'username': 'dr.gupta', 'email': 'dr.gupta@hospital.com', 'password': 'doctor123',
        'full_name': 'Dr. Amit Gupta', 'specialization': 'General Physician', 'department': 'General Medicine',
        'phone': '9876543214', 'qualification': 'MBBS, MD Medicine', 'experience': 20, 'fee': 350.0},
    ]
    
    # Create doctors
    for docData in sampleDoctors:
        # Create user account
        newUser = User(
            username=docData['username'],
            email=docData['email'],
            role='doctor'
        )
        newUser.set_password(docData['password'])
        db.session.add(newUser)
        db.session.flush()
        
        dept = Department.query.filter_by(name=docData['department']).first()
        
        newDoctor = Doctor(
            user_id=newUser.id,
            full_name=docData['full_name'],
            specialization=docData['specialization'],
            department_id=dept.id if dept else 1,
            phone=docData['phone'],
            qualification=docData['qualification'],
            experience_years=docData['experience'],
            consultation_fee=docData['fee']
        )
        db.session.add(newDoctor)
        db.session.flush()
        
        # Add availability for next 7 days
        today = datetime.now().date()
        for i in range(7):
            availDate = today + timedelta(days=i)
            availability = DoctorAvailability(
                doctor_id=newDoctor.id,
                date=availDate,
                start_time=time(9, 0),
                end_time=time(17, 0),
                is_available=True
            )
            db.session.add(availability)
    
    # Sample patients data
    samplePatients = [
        {'username': 'patient1', 'email': 'patient1@email.com', 'password': 'patient123',
        'full_name': 'Rahul Verma', 'phone': '9123456780', 'dob': '1990-05-15',
        'gender': 'Male', 'blood_group': 'O+', 'address': '123 MG Road, Mumbai'},
        
        {'username': 'patient2', 'email': 'patient2@email.com', 'password': 'patient123',
        'full_name': 'Sneha Reddy', 'phone': '9123456781', 'dob': '1995-08-20',
        'gender': 'Female', 'blood_group': 'A+', 'address': '456 Park Street, Delhi'},
        
        {'username': 'patient3', 'email': 'patient3@email.com', 'password': 'patient123',
        'full_name': 'Arjun Singh', 'phone': '9123456782', 'dob': '1988-12-10',
        'gender': 'Male', 'blood_group': 'B+', 'address': '789 Brigade Road, Bangalore'},
        
        {'username': 'patient4', 'email': 'patient4@email.com', 'password': 'patient123',
        'full_name': 'Pooja Iyer', 'phone': '9123456783', 'dob': '1992-03-25',
        'gender': 'Female', 'blood_group': 'AB+', 'address': '321 Anna Salai, Chennai'},
    ]
    
    # Create patients
    for patData in samplePatients:
        # Create user account
        newUser = User(
            username=patData['username'],
            email=patData['email'],
            role='patient'
        )
        newUser.set_password(patData['password'])
        db.session.add(newUser)
        db.session.flush()
        
        # Parse date of birth
        dob = datetime.strptime(patData['dob'], '%Y-%m-%d').date()
        
        newPatient = Patient(
            user_id=newUser.id,
            full_name=patData['full_name'],
            phone=patData['phone'],
            date_of_birth=dob,
            gender=patData['gender'],
            blood_group=patData['blood_group'],
            address=patData['address']
        )
        db.session.add(newPatient)
    
    # Commit all 
    db.session.commit()
    print("Sample doctors and patients created successfully!")


# Custom decorator for admin access control
def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        isAuthenticated = current_user.is_authenticated
        
        if not isAuthenticated:
            abort(403)
        
        userRole = current_user.role
        if userRole != 'admin':
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


# Custom decorator for doctor access control
def doctor_required(f):
    """Decorator to require doctor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        isAuthenticated = current_user.is_authenticated
        
        if not isAuthenticated:
            abort(403)
        
        userRole = current_user.role
        if userRole != 'doctor':
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


# Custom decorator for patient access control
def patient_required(f):
    """Decorator to require patient role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        isAuthenticated = current_user.is_authenticated
        
        if isAuthenticated == False:
            abort(403)
        
        userRole = current_user.role
        
        if userRole != 'patient':
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function
