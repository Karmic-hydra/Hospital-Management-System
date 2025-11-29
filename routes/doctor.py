from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models import Doctor, Appointment, Treatment, Patient, DoctorAvailability
from utils import doctor_required
from datetime import datetime, timedelta, time

doctor_bp = Blueprint('doctor', __name__)


@doctor_bp.route('/dashboard')
@login_required
@doctor_required
def dashboard():
    # Get current doctor profile
    currentUserId = current_user.id
    currentDoctor = Doctor.query.filter_by(user_id=currentUserId).first()
    
    # Check if doctor exists - debugging is important here !!!!
    if currentDoctor is None:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Get today's appointments - this part is tricky!
    todayDate = datetime.now().date()
    doctorId = currentDoctor.id
    
    todayAppointments = Appointment.query.filter_by(
        doctor_id=doctorId,
        appointment_date=todayDate
    ).order_by(Appointment.appointment_time).all()
    
    # Get this week's appointments
    weekStartDate = todayDate
    weekEndDate = todayDate + timedelta(days=7)
    
    weekAppointments = Appointment.query.filter(
        Appointment.doctor_id == doctorId,
        Appointment.appointment_date >= weekStartDate,
        Appointment.appointment_date <= weekEndDate,
        Appointment.status == 'Booked'
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    allAppointments = Appointment.query.filter_by(doctor_id=doctorId).all()
    uniquePatients = set()
    for appointment in allAppointments:
        patientId = appointment.patient_id
        uniquePatients.add(patientId)
    
    patientCount = len(uniquePatients)
    
    # Get completed appointments count
    completedAppointments = Appointment.query.filter_by(
        doctor_id=doctorId,
        status='Completed'
    ).all()
    completedCount = len(completedAppointments)
    
    return render_template('doctor/dashboard.html',
                        doctor=currentDoctor,
                        today_appointments=todayAppointments,
                        week_appointments=weekAppointments,
                        patient_count=patientCount,
                        completed_count=completedCount)


@doctor_bp.route('/appointments')
@login_required
@doctor_required
def appointments():
    currentDoctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    statusFilter = request.args.get('status', '').strip()
    dateFilter = request.args.get('date', '').strip()
    
    baseQuery = Appointment.query.filter_by(doctor_id=currentDoctor.id)
    
    # Apply status filter if provided - this part is tricky!
    hasStatusFilter = len(statusFilter) > 0
    if hasStatusFilter:
        baseQuery = baseQuery.filter_by(status=statusFilter)
    
    # Apply date filter if provided
    hasDateFilter = len(dateFilter) > 0
    if hasDateFilter:
        parsedDate = datetime.strptime(dateFilter, '%Y-%m-%d').date()
        baseQuery = baseQuery.filter_by(appointment_date=parsedDate)
    
    # Execute query with sorting
    doctorAppointments = baseQuery.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('doctor/appointments.html', appointments=doctorAppointments, doctor=currentDoctor)


@doctor_bp.route('/appointment/<int:appointment_id>')
@login_required
@doctor_required
def view_appointment(appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.filter_by(id=appointment_id, doctor_id=doctor.id).first_or_404()
    
    # Get patient's appointment history
    patient_history = Appointment.query.filter_by(
        patient_id=appointment.patient_id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('doctor/view_appointment.html',
                        appointment=appointment,
                        patient_history=patient_history)


@doctor_bp.route('/appointment/<int:appointment_id>/complete', methods=['GET', 'POST'])
@login_required
@doctor_required
def complete_appointment(appointment_id):
    # Get current doctor profile
    currentDoctor = Doctor.query.filter_by(user_id=current_user.id).first()
    selectedAppointment = Appointment.query.filter_by(id=appointment_id, doctor_id=currentDoctor.id).first_or_404()
    
    # Check appointment status - debugging is important here !!!!
    appointmentStatus = selectedAppointment.status
    isBookedStatus = appointmentStatus == 'Booked'
    
    if not isBookedStatus:
        flash('This appointment cannot be completed.', 'warning')
        return redirect(url_for('doctor.view_appointment', appointment_id=appointment_id))
    
    if request.method == 'POST':
        patientDiagnosis = request.form.get('diagnosis', '').strip()
        doctorPrescription = request.form.get('prescription', '').strip()
        treatmentNotes = request.form.get('notes', '').strip()
        followUpDate = request.form.get('follow_up_date', '').strip()
        
        hasDiagnosis = len(patientDiagnosis) > 0
        if not hasDiagnosis:
            flash('Diagnosis is required.', 'danger')
            return render_template('doctor/complete_appointment.html', appointment=selectedAppointment)
        
        try:
            # Create treatment record - this part is tricky!
            newTreatment = Treatment(
                appointment_id=selectedAppointment.id,
                diagnosis=patientDiagnosis,
                prescription=doctorPrescription,
                notes=treatmentNotes
            )
            
            # Add follow-up date if provided
            hasFollowUp = len(followUpDate) > 0
            if hasFollowUp:
                parsedFollowUpDate = datetime.strptime(followUpDate, '%Y-%m-%d').date()
                newTreatment.follow_up_date = parsedFollowUpDate
            
            # Update appointment status
            selectedAppointment.status = 'Completed'
            
            # Save to database
            db.session.add(newTreatment)
            db.session.commit()
            
            flash('Appointment completed successfully!', 'success')
            return redirect(url_for('doctor.appointments'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while completing the appointment.', 'danger')
            print(f"Error completing appointment: {e}")
    
    return render_template('doctor/complete_appointment.html', appointment=selectedAppointment)


@doctor_bp.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@doctor_required
def cancel_appointment(appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.filter_by(id=appointment_id, doctor_id=doctor.id).first_or_404()
    
    if appointment.status != 'Booked':
        flash('This appointment cannot be cancelled.', 'warning')
        return redirect(url_for('doctor.appointments'))
    
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        flash('Appointment cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the appointment.', 'danger')
        print(f"Error cancelling appointment: {e}")
    
    return redirect(url_for('doctor.appointments'))


@doctor_bp.route('/patients')
@login_required
@doctor_required
def patients():
    currentDoctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    # This part is tricky - avoid duplicates!
    allAppointments = Appointment.query.filter_by(doctor_id=currentDoctor.id).all()
    
    uniquePatientIds = set()
    for booking in allAppointments:
        patientId = booking.patient_id
        uniquePatientIds.add(patientId)
    
    patientIdsList = list(uniquePatientIds)
    
    # Debugging is important here !!!!
    patientsList = Patient.query.filter(Patient.id.in_(patientIdsList)).all()
    
    return render_template('doctor/patients.html', patients=patientsList, doctor=currentDoctor)


@doctor_bp.route('/patient/<int:patient_id>')
@login_required
@doctor_required
def view_patient(patient_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    
    # Get patient's appointment history with this doctor
    appointments = Appointment.query.filter_by(
        patient_id=patient_id,
        doctor_id=doctor.id
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('doctor/view_patient.html',
                         patient=patient,
                         appointments=appointments)


@doctor_bp.route('/availability', methods=['GET', 'POST'])
@login_required
@doctor_required
def availability():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        try:
            # Clear existing availability for next 7 days
            today = datetime.now().date()
            week_end = today + timedelta(days=7)
            
            DoctorAvailability.query.filter(
                DoctorAvailability.doctor_id == doctor.id,
                DoctorAvailability.date >= today,
                DoctorAvailability.date <= week_end
            ).delete()
            
            # Add new availability
            for i in range(7):
                date = today + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                is_available = request.form.get(f'available_{date_str}') == 'on'
                
                if is_available:
                    start_time_str = request.form.get(f'start_time_{date_str}', '09:00')
                    end_time_str = request.form.get(f'end_time_{date_str}', '17:00')
                    
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    availability = DoctorAvailability(
                        doctor_id=doctor.id,
                        date=date,
                        start_time=start_time,
                        end_time=end_time,
                        is_available=True
                    )
                    db.session.add(availability)
            
            db.session.commit()
            flash('Availability updated successfully!', 'success')
            return redirect(url_for('doctor.availability'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating availability.', 'danger')
            print(f"Error updating availability: {e}")
    
    # Get current availability for next 7 days
    today = datetime.now().date()
    availability_data = []
    
    for i in range(7):
        date = today + timedelta(days=i)
        avail = DoctorAvailability.query.filter_by(
            doctor_id=doctor.id,
            date=date
        ).first()
        
        availability_data.append({
            'date': date,
            'available': avail is not None and avail.is_available,
            'start_time': avail.start_time.strftime('%H:%M') if avail else '09:00',
            'end_time': avail.end_time.strftime('%H:%M') if avail else '17:00'
        })
    
    return render_template('doctor/availability.html',
                         doctor=doctor,
                         availability_data=availability_data)


@doctor_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@doctor_required
def profile():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        qualification = request.form.get('qualification', '').strip()
        
        try:
            doctor.phone = phone
            doctor.qualification = qualification
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('doctor.profile'))
        
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating profile.', 'danger')
            print(f"Error updating profile: {e}")
    
    return render_template('doctor/profile.html', doctor=doctor)
