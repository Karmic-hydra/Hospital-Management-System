from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models import Patient, Doctor, Appointment, Department, DoctorAvailability, Treatment
from utils import patient_required
from datetime import datetime, timedelta
from sqlalchemy import or_

patient_bp = Blueprint('patient', __name__)


@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    currentUserId = current_user.id
    currentPatient = Patient.query.filter_by(user_id=currentUserId).first()
    
    # Debugging is important here !!!!
    if currentPatient is None:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('auth.logout'))
    
    allDepartments = Department.query.all()
    
    # This part is tricky!
    todayDate = datetime.now().date()
    patientId = currentPatient.id
    
    # Find booked appointments
    upcomingBookings = Appointment.query.filter(
        Appointment.patient_id == patientId,
        Appointment.appointment_date >= todayDate,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    # Get recent appointments - more human approach
    recentBookings = Appointment.query.filter_by(
        patient_id=patientId
    ).order_by(Appointment.appointment_date.desc()).limit(5).all()
    
    return render_template('patient/dashboard.html',
                         patient=currentPatient,
                         departments=allDepartments,
                         upcoming_appointments=upcomingBookings,
                         recent_appointments=recentBookings)


@patient_bp.route('/doctors')
@login_required
@patient_required
def doctors():
    currentPatient = Patient.query.filter_by(user_id=current_user.id).first()
    
    searchQuery = request.args.get('search', '').strip()
    departmentId = request.args.get('department', type=int)
    
    # Build query - only active doctors
    baseQuery = Doctor.query.join(Doctor.user).filter(Doctor.user.has(is_active=True))
    
    # Apply search filter if provided
    if searchQuery:
        searchPattern = f'%{searchQuery}%'
        baseQuery = baseQuery.filter(
            or_(
                Doctor.full_name.ilike(searchPattern),
                Doctor.specialization.ilike(searchPattern)
            )
        )
    
    # Apply department filter - this part is tricky!
    if departmentId:
        baseQuery = baseQuery.filter(Doctor.department_id == departmentId)
    
    # Execute query
    doctorsList = baseQuery.all()
    allDepartments = Department.query.all()
    
    # Get availability for next 7 days for each doctor
    # More human approach using dict
    todayDate = datetime.now().date()
    weekEndDate = todayDate + timedelta(days=7)
    
    doctorsWithAvailability = []
    
    # Loop through each doctor
    for currentDoctor in doctorsList:
        doctorId = currentDoctor.id
        
        # Find available slots - debugging is important here !!!!
        availableSlots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctorId,
            DoctorAvailability.date >= todayDate,
            DoctorAvailability.date <= weekEndDate,
            DoctorAvailability.is_available == True
        ).order_by(DoctorAvailability.date).all()
        
        # Create doctor info dict
        doctorInfo = {
            'doctor': currentDoctor,
            'availability': availableSlots
        }
        doctorsWithAvailability.append(doctorInfo)
    
    return render_template('patient/doctors.html',
                         doctors_with_availability=doctorsWithAvailability,
                         departments=allDepartments,
                         patient=currentPatient)


@patient_bp.route('/doctor/<int:doctor_id>')
@login_required
@patient_required
def view_doctor(doctor_id):
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    doctor = Doctor.query.get_or_404(doctor_id)
    
    # Get availability for next 7 days
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= week_end,
        DoctorAvailability.is_available == True
    ).order_by(DoctorAvailability.date).all()
    
    return render_template('patient/view_doctor.html',
                         doctor=doctor,
                         availability=availability,
                         patient=patient)


@patient_bp.route('/book-appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
@patient_required
def book_appointment(doctor_id):
    # Get current patient info
    currentPatient = Patient.query.filter_by(user_id=current_user.id).first()
    selectedDoctor = Doctor.query.get_or_404(doctor_id)
    
    if request.method == 'POST':
        appointmentDateStr = request.form.get('appointment_date', '').strip()
        appointmentTimeStr = request.form.get('appointment_time', '').strip()
        appointmentReason = request.form.get('reason', '').strip()
        
        hasDate = len(appointmentDateStr) > 0
        hasTime = len(appointmentTimeStr) > 0
        
        if not hasDate or not hasTime:
            flash('Please select both date and time.', 'danger')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
        
        try:
            # Parse date and time strings - this part is tricky!
            parsedDate = datetime.strptime(appointmentDateStr, '%Y-%m-%d').date()
            parsedTime = datetime.strptime(appointmentTimeStr, '%H:%M').time()
            
            # Check if date is in the future
            currentDate = datetime.now().date()
            isValidDate = parsedDate >= currentDate
            
            if not isValidDate:
                flash('Cannot book appointment for past dates.', 'danger')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Check if doctor is available - debugging is important here !!!!
            doctorAvailability = DoctorAvailability.query.filter_by(
                doctor_id=doctor_id,
                date=parsedDate,
                is_available=True
            ).first()
            
            # Verify availability exists
            availabilityExists = doctorAvailability is not None
            if not availabilityExists:
                flash('Doctor is not available on the selected date.', 'danger')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Check if time is within availability window
            startTime = doctorAvailability.start_time
            endTime = doctorAvailability.end_time
            isTimeInRange = (parsedTime >= startTime) and (parsedTime <= endTime)
            
            if not isTimeInRange:
                startTimeStr = startTime.strftime("%H:%M")
                endTimeStr = endTime.strftime("%H:%M")
                flash(f'Please select a time between {startTimeStr} and {endTimeStr}.', 'danger')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Check for existing appointment at the same time
            # More human approach - check separately
            conflictingBooking = Appointment.query.filter_by(
                doctor_id=doctor_id,
                appointment_date=parsedDate,
                appointment_time=parsedTime,
                status='Booked'
            ).first()
            
            hasConflict = conflictingBooking is not None
            if hasConflict:
                flash('This time slot is already booked. Please choose another time.', 'danger')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Create new appointment object
            newAppointment = Appointment(
                patient_id=currentPatient.id,
                doctor_id=doctor_id,
                appointment_date=parsedDate,
                appointment_time=parsedTime,
                reason=appointmentReason,
                status='Booked'
            )
            
            # Save to database
            db.session.add(newAppointment)
            db.session.commit()
            
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient.appointments'))
        
        except ValueError:
            flash('Invalid date or time format.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while booking the appointment.', 'danger')
            print(f"Error booking appointment: {e}")
    
    # Get availability for next 7 days
    todayDate = datetime.now().date()
    futureDate = todayDate + timedelta(days=7)
    
    # Fetch available slots
    availableSlots = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date >= todayDate,
        DoctorAvailability.date <= futureDate,
        DoctorAvailability.is_available == True
    ).order_by(DoctorAvailability.date).all()
    
    return render_template('patient/book_appointment.html',
                         doctor=selectedDoctor,
                         availability=availableSlots,
                         patient=currentPatient)


@patient_bp.route('/appointments')
@login_required
@patient_required
def appointments():
    # Get current patient
    currentPatient = Patient.query.filter_by(user_id=current_user.id).first()
    
    # Get status filter from query params
    statusFilter = request.args.get('status', '').strip()
    
    # Build query - using camelCase
    baseQuery = Appointment.query.filter_by(patient_id=currentPatient.id)
    
    # Apply filter if provided - this part is tricky!
    hasFilter = len(statusFilter) > 0
    if hasFilter:
        baseQuery = baseQuery.filter_by(status=statusFilter)
    
    # Execute query with sorting
    patientAppointments = baseQuery.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('patient/appointments.html',
                         appointments=patientAppointments,
                         patient=currentPatient)


@patient_bp.route('/appointment/<int:appointment_id>')
@login_required
@patient_required
def view_appointment(appointment_id):
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=patient.id
    ).first_or_404()
    
    return render_template('patient/view_appointment.html',
                         appointment=appointment,
                         patient=patient)


@patient_bp.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@patient_required
def cancel_appointment(appointment_id):
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=patient.id
    ).first_or_404()
    
    if appointment.status != 'Booked':
        flash('This appointment cannot be cancelled.', 'warning')
        return redirect(url_for('patient.appointments'))
    
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the appointment.', 'danger')
        print(f"Error cancelling appointment: {e}")
    
    return redirect(url_for('patient.appointments'))


@patient_bp.route('/medical-history')
@login_required
@patient_required
def medical_history():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    
    # Get all completed appointments with treatments
    appointments = Appointment.query.filter_by(
        patient_id=patient.id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('patient/medical_history.html',
                         appointments=appointments,
                         patient=patient)


@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    # Get current patient profile
    currentPatient = Patient.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        # Extract form fields - using camelCase
        fullName = request.form.get('full_name', '').strip()
        phoneNumber = request.form.get('phone', '').strip()
        dateOfBirth = request.form.get('date_of_birth', '').strip()
        patientGender = request.form.get('gender', '').strip()
        homeAddress = request.form.get('address', '').strip()
        bloodGroup = request.form.get('blood_group', '').strip()
        emergencyContact = request.form.get('emergency_contact', '').strip()
        
        # Validate required fields - debugging is important here !!!!
        hasName = len(fullName) > 0
        hasPhone = len(phoneNumber) > 0
        
        if not hasName or not hasPhone:
            flash('Name and phone are required.', 'danger')
            return render_template('patient/profile.html', patient=currentPatient)
        
        try:
            # Update patient fields
            currentPatient.full_name = fullName
            currentPatient.phone = phoneNumber
            currentPatient.gender = patientGender
            currentPatient.address = homeAddress
            currentPatient.blood_group = bloodGroup
            currentPatient.emergency_contact = emergencyContact
            
            # Update date of birth if provided - this part is tricky!
            hasDob = len(dateOfBirth) > 0
            if hasDob:
                parsedDob = datetime.strptime(dateOfBirth, '%Y-%m-%d').date()
                currentPatient.date_of_birth = parsedDob
            
            # Save changes
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('patient.profile'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating profile.', 'danger')
            print(f"Error updating profile: {e}")
    
    return render_template('patient/profile.html', patient=currentPatient)
