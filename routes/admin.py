from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import User, Doctor, Patient, Appointment, Treatment, Department, DoctorAvailability
from utils import admin_required
from datetime import datetime, timedelta
from sqlalchemy import or_, func

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # This part is tricky!
    activeDoctorsCount = 0
    allDoctors = Doctor.query.join(User).all()
    for doc in allDoctors:
        if doc.user.is_active == True:
            activeDoctorsCount = activeDoctorsCount + 1
    
    # Count active patients
    activePatientsCount = 0
    allPatients = Patient.query.join(User).all()
    for pat in allPatients:
        if pat.user.is_active == True:
            activePatientsCount = activePatientsCount + 1
    
    totalAppointments = Appointment.query.count()
    
    # Get today's appointments - debugging is important here !!!!
    currentDate = datetime.now().date()
    todayAppointments = Appointment.query.filter_by(appointment_date=currentDate).count()
    
    # Get upcoming appointments
    upcomingBookings = Appointment.query.filter(
        Appointment.appointment_date >= currentDate,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(10).all()
    
    # Get recent patients - using dict for better organization
    recentPatientsList = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    
    # Department statistics - more human approach
    allDepartments = Department.query.all()
    departmentStats = []
    
    # Loop through each department
    for currentDept in allDepartments:
        deptId = currentDept.id
        # Count doctors in this department
        doctorCount = 0
        deptDoctors = Doctor.query.filter_by(department_id=deptId).all()
        for doctor in deptDoctors:
            if doctor.user.is_active:
                doctorCount += 1
        
        # Store stats
        deptInfo = {
            'name': currentDept.name,
            'doctor_count': doctorCount
        }
        departmentStats.append(deptInfo)
    
    return render_template('admin/dashboard.html',
                        total_doctors=activeDoctorsCount,
                        total_patients=activePatientsCount,
                        total_appointments=totalAppointments,
                        today_appointments=todayAppointments,
                        upcoming_appointments=upcomingBookings,
                        recent_patients=recentPatientsList,
                        dept_stats=departmentStats)


@admin_bp.route('/doctors')
@login_required
@admin_required
def doctors():
    # Get search parameters
    searchQuery = request.args.get('search', '').strip()
    departmentId = request.args.get('department', type=int)
    status_filter = request.args.get('status', 'active').strip()
    
    # Start with base query
    baseQuery = Doctor.query.join(User)
    
    # Filter by active/inactive status
    if status_filter == 'active':
        baseQuery = baseQuery.filter(User.is_active == True)
    elif status_filter == 'inactive':
        baseQuery = baseQuery.filter(User.is_active == False)
    
    # Apply search filter if provided
    if searchQuery:
        # Search in name or specialization
        searchPattern = f'%{searchQuery}%'
        baseQuery = baseQuery.filter(
            or_(
                Doctor.full_name.ilike(searchPattern),
                Doctor.specialization.ilike(searchPattern)
            )
        )
    
    # Apply department filter if selected
    # This part is tricky!
    if departmentId:
        baseQuery = baseQuery.filter(Doctor.department_id == departmentId)
    
    # Execute query and get results
    doctorsList = baseQuery.all()
    allDepartments = Department.query.all()
    
    return render_template('admin/doctors.html', doctors=doctorsList, departments=allDepartments)


@admin_bp.route('/doctors/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_doctor():
    if request.method == 'POST':
        userName = request.form.get('username', '').strip()
        userEmail = request.form.get('email', '').strip()
        userPassword = request.form.get('password', '').strip()
        fullName = request.form.get('full_name', '').strip()
        doctorSpecialization = request.form.get('specialization', '').strip()
        departmentId = request.form.get('department_id', type=int)
        phoneNumber = request.form.get('phone', '').strip()
        qualification = request.form.get('qualification', '').strip()
        experienceYears = request.form.get('experience_years', type=int)
        consultationFee = request.form.get('consultation_fee', type=float)
        
        # Validation - check required fields
        # Debugging is important here !!!!
        requiredFields = [userName, userEmail, userPassword, fullName, doctorSpecialization, departmentId]
        isValid = True
        for field in requiredFields:
            if field is None or field == '':
                isValid = False
                break
        
        if not isValid:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.add_doctor'))
        
        # Check if username already exists - more human approach
        existingUserByUsername = User.query.filter_by(username=userName).first()
        if existingUserByUsername is not None:
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.add_doctor'))
        
        # Check if email already exists
        existingUserByEmail = User.query.filter_by(email=userEmail).first()
        if existingUserByEmail is not None:
            flash('Email already registered.', 'danger')
            return redirect(url_for('admin.add_doctor'))
        
        # Try to create new doctor
        try:
            # Create user account first - this part is tricky!
            newUser = User(
                username=userName,
                email=userEmail,
                role='doctor'
            )
            newUser.set_password(userPassword)
            db.session.add(newUser)
            db.session.flush()  # Get user ID
            
            # Get the newly created user's ID
            newUserId = newUser.id
            
            # Create doctor profile
            newDoctor = Doctor(
                user_id=newUserId,
                full_name=fullName,
                specialization=doctorSpecialization,
                department_id=departmentId,
                phone=phoneNumber,
                qualification=qualification,
                experience_years=experienceYears,
                consultation_fee=consultationFee
            )
            db.session.add(newDoctor)
            db.session.commit()
            
            flash(f'Doctor {fullName} added successfully!', 'success')
            return redirect(url_for('admin.doctors'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the doctor.', 'danger')
            print(f"Error adding doctor: {e}")
    
    # GET request - show form
    allDepartments = Department.query.all()
    return render_template('admin/add_doctor.html', departments=allDepartments)


@admin_bp.route('/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        specialization = request.form.get('specialization', '').strip()
        department_id = request.form.get('department_id', type=int)
        phone = request.form.get('phone', '').strip()
        qualification = request.form.get('qualification', '').strip()
        experience_years = request.form.get('experience_years', type=int)
        consultation_fee = request.form.get('consultation_fee', type=float)
        email = request.form.get('email', '').strip()
        
        # Validation
        if not all([full_name, specialization, department_id, email]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.edit_doctor', doctor_id=doctor_id))
        
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != doctor.user_id:
            flash('Email already registered to another user.', 'danger')
            return redirect(url_for('admin.edit_doctor', doctor_id=doctor_id))
        
        try:
            doctor.full_name = full_name
            doctor.specialization = specialization
            doctor.department_id = department_id
            doctor.phone = phone
            doctor.qualification = qualification
            doctor.experience_years = experience_years
            doctor.consultation_fee = consultation_fee
            doctor.user.email = email
            
            db.session.commit()
            flash(f'Doctor {full_name} updated successfully!', 'success')
            return redirect(url_for('admin.doctors'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the doctor.', 'danger')
            print(f"Error updating doctor: {e}")
    
    departments = Department.query.all()
    return render_template('admin/edit_doctor.html', doctor=doctor, departments=departments)


@admin_bp.route('/doctors/delete/<int:doctor_id>', methods=['POST'])
@login_required
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    try:
        # Deactivate user instead of deleting
        doctor.user.is_active = False
        db.session.commit()
        flash(f'Doctor {doctor.full_name} has been deactivated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deactivating the doctor.', 'danger')
        print(f"Error deactivating doctor: {e}")
    
    return redirect(url_for('admin.doctors'))


@admin_bp.route('/doctors/reactivate/<int:doctor_id>', methods=['POST'])
@login_required
@admin_required
def reactivate_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    try:
        # Reactivate user account
        doctor.user.is_active = True
        db.session.commit()
        flash(f'Doctor {doctor.full_name} has been reactivated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while reactivating the doctor.', 'danger')
        print(f"Error reactivating doctor: {e}")
    
    return redirect(url_for('admin.doctors'))


@admin_bp.route('/patients')
@login_required
@admin_required
def patients():
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'active').strip()
    
    query = Patient.query.join(User)
    
    # Filter by active/inactive status
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    # 'all' shows both active and inactive
    
    if search_query:
        query = query.filter(
            or_(
                Patient.full_name.ilike(f'%{search_query}%'),
                Patient.phone.ilike(f'%{search_query}%'),
                Patient.id == int(search_query) if search_query.isdigit() else False
            )
        )
    
    patients = query.all()
    
    return render_template('admin/patients.html', patients=patients)


@admin_bp.route('/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        date_of_birth = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', '').strip()
        address = request.form.get('address', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()
        medical_history = request.form.get('medical_history', '').strip()
        
        if not all([full_name, phone, email]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.edit_patient', patient_id=patient_id))
        
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != patient.user_id:
            flash('Email already registered to another user.', 'danger')
            return redirect(url_for('admin.edit_patient', patient_id=patient_id))
        
        try:
            patient.full_name = full_name
            patient.phone = phone
            patient.user.email = email
            patient.gender = gender
            patient.address = address
            patient.blood_group = blood_group
            patient.emergency_contact = emergency_contact
            patient.medical_history = medical_history
            
            if date_of_birth:
                patient.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            
            db.session.commit()
            flash(f'Patient {full_name} updated successfully!', 'success')
            return redirect(url_for('admin.patients'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the patient.', 'danger')
            print(f"Error updating patient: {e}")
    
    return render_template('admin/edit_patient.html', patient=patient)


@admin_bp.route('/patients/delete/<int:patient_id>', methods=['POST'])
@login_required
@admin_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        # Deactivate user instead of deleting
        patient.user.is_active = False
        db.session.commit()
        flash(f'Patient {patient.full_name} has been deactivated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deactivating the patient.', 'danger')
        print(f"Error deactivating patient: {e}")
    
    return redirect(url_for('admin.patients'))


@admin_bp.route('/patients/reactivate/<int:patient_id>', methods=['POST'])
@login_required
@admin_required
def reactivate_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        # Reactivate user account
        patient.user.is_active = True
        db.session.commit()
        flash(f'Patient {patient.full_name} has been reactivated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while reactivating the patient.', 'danger')
        print(f"Error reactivating patient: {e}")
    
    return redirect(url_for('admin.patients'))


@admin_bp.route('/appointments')
@login_required
@admin_required
def appointments():
    status_filter = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()
    
    query = Appointment.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if date_filter:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter_by(appointment_date=filter_date)
    
    appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    
    return render_template('admin/appointments.html', appointments=appointments)


@admin_bp.route('/patient/<int:patient_id>')
@login_required
@admin_required
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(
        Appointment.appointment_date.desc()
    ).all()
    
    return render_template('admin/view_patient.html', patient=patient, appointments=appointments)


@admin_bp.route('/doctor/<int:doctor_id>')
@login_required
@admin_required
def view_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    appointments = Appointment.query.filter_by(doctor_id=doctor_id).order_by(
        Appointment.appointment_date.desc()
    ).all()
    
    return render_template('admin/view_doctor.html', doctor=doctor, appointments=appointments)


@admin_bp.route('/appointment/<int:appointment_id>')
@login_required
@admin_required
def view_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template('admin/view_appointment.html', appointment=appointment)


@admin_bp.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.status != 'Booked':
        flash('Only booked appointments can be cancelled.', 'warning')
        return redirect(url_for('admin.appointments'))
    
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the appointment.', 'danger')
        print(f"Error cancelling appointment: {e}")
    
    return redirect(url_for('admin.appointments'))


@admin_bp.route('/reset-password/<user_type>/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_password(user_type, user_id):
    newPassword = request.form.get('new_password', '').strip()
    
    if not newPassword or len(newPassword) < 6:
        flash('Password must be at least 6 characters long.', 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))
    
    try:
        if user_type == 'doctor':
            doctor = Doctor.query.get_or_404(user_id)
            user = doctor.user
            userName = doctor.full_name
        elif user_type == 'patient':
            patient = Patient.query.get_or_404(user_id)
            user = patient.user
            userName = patient.full_name
        else:
            flash('Invalid user type.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        # Reset password
        user.set_password(newPassword)
        db.session.commit()
        
        flash(f'Password reset successfully for {userName}. New password: {newPassword}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while resetting the password.', 'danger')
        print(f"Error resetting password: {e}")
    
    return redirect(request.referrer or url_for('admin.dashboard'))
