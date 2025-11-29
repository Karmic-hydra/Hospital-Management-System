from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import Doctor, Patient, Appointment, Department, User
from datetime import datetime
from sqlalchemy import or_

api_bp = Blueprint('api', __name__)


# Doctors API
@api_bp.route('/doctors', methods=['GET'])
@login_required
def get_doctors():
    """Get all doctors with optional filtering"""
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    
    query = Doctor.query.join(User).filter(User.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                Doctor.full_name.ilike(f'%{search}%'),
                Doctor.specialization.ilike(f'%{search}%')
            )
        )
    
    if department_id:
        query = query.filter(Doctor.department_id == department_id)
    
    doctors = query.all()
    
    return jsonify({
        'success': True,
        'count': len(doctors),
        'doctors': [{
            'id': doc.id,
            'full_name': doc.full_name,
            'specialization': doc.specialization,
            'department': doc.department.name,
            'phone': doc.phone,
            'qualification': doc.qualification,
            'experience_years': doc.experience_years,
            'consultation_fee': doc.consultation_fee
        } for doc in doctors]
    })


@api_bp.route('/doctors/<int:doctor_id>', methods=['GET'])
@login_required
def get_doctor(doctor_id):
    """Get a specific doctor by ID"""
    doctor = Doctor.query.get_or_404(doctor_id)
    
    return jsonify({
        'success': True,
        'doctor': {
            'id': doctor.id,
            'full_name': doctor.full_name,
            'specialization': doctor.specialization,
            'department': doctor.department.name,
            'department_id': doctor.department_id,
            'phone': doctor.phone,
            'qualification': doctor.qualification,
            'experience_years': doctor.experience_years,
            'consultation_fee': doctor.consultation_fee,
            'email': doctor.user.email
        }
    })


@api_bp.route('/doctors/<int:doctor_id>', methods=['PUT'])
@login_required
def update_doctor(doctor_id):
    """Update doctor information (Admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    doctor = Doctor.query.get_or_404(doctor_id)
    data = request.get_json()
    
    try:
        if 'full_name' in data:
            doctor.full_name = data['full_name']
        if 'specialization' in data:
            doctor.specialization = data['specialization']
        if 'department_id' in data:
            doctor.department_id = data['department_id']
        if 'phone' in data:
            doctor.phone = data['phone']
        if 'qualification' in data:
            doctor.qualification = data['qualification']
        if 'experience_years' in data:
            doctor.experience_years = data['experience_years']
        if 'consultation_fee' in data:
            doctor.consultation_fee = data['consultation_fee']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Doctor updated successfully',
            'doctor': {
                'id': doctor.id,
                'full_name': doctor.full_name,
                'specialization': doctor.specialization
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/doctors/<int:doctor_id>', methods=['DELETE'])
@login_required
def delete_doctor(doctor_id):
    """Deactivate a doctor (Admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    doctor = Doctor.query.get_or_404(doctor_id)
    
    try:
        doctor.user.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Doctor {doctor.full_name} deactivated successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Patients API
@api_bp.route('/patients', methods=['GET'])
@login_required
def get_patients():
    """Get all patients (Admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    search = request.args.get('search', '').strip()
    
    query = Patient.query.join(User).filter(User.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                Patient.full_name.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%')
            )
        )
    
    patients = query.all()
    
    return jsonify({
        'success': True,
        'count': len(patients),
        'patients': [{
            'id': pat.id,
            'full_name': pat.full_name,
            'phone': pat.phone,
            'email': pat.user.email,
            'gender': pat.gender,
            'blood_group': pat.blood_group,
            'date_of_birth': pat.date_of_birth.isoformat() if pat.date_of_birth else None
        } for pat in patients]
    })


@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
@login_required
def get_patient(patient_id):
    """Get a specific patient"""
    # Patients can only view their own data
    if current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient or patient.id != patient_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    patient = Patient.query.get_or_404(patient_id)
    
    return jsonify({
        'success': True,
        'patient': {
            'id': patient.id,
            'full_name': patient.full_name,
            'phone': patient.phone,
            'email': patient.user.email,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'gender': patient.gender,
            'address': patient.address,
            'blood_group': patient.blood_group,
            'emergency_contact': patient.emergency_contact,
            'medical_history': patient.medical_history
        }
    })


# Appointments API
@api_bp.route('/appointments', methods=['GET'])
@login_required
def get_appointments():
    """Get appointments based on user role"""
    status = request.args.get('status', '').strip()
    date = request.args.get('date', '').strip()
    
    if current_user.role == 'admin':
        query = Appointment.query
    elif current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        query = Appointment.query.filter_by(doctor_id=doctor.id)
    elif current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        query = Appointment.query.filter_by(patient_id=patient.id)
    else:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if status:
        query = query.filter_by(status=status)
    
    if date:
        try:
            filter_date = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter_by(appointment_date=filter_date)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    
    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    
    return jsonify({
        'success': True,
        'count': len(appointments),
        'appointments': [{
            'id': apt.id,
            'patient_name': apt.patient.full_name,
            'doctor_name': apt.doctor.full_name,
            'appointment_date': apt.appointment_date.isoformat(),
            'appointment_time': apt.appointment_time.strftime('%H:%M'),
            'status': apt.status,
            'reason': apt.reason
        } for apt in appointments]
    })


@api_bp.route('/appointments/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment(appointment_id):
    """Get a specific appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check authorization
    if current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        if appointment.doctor_id != doctor.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    elif current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if appointment.patient_id != patient.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    result = {
        'id': appointment.id,
        'patient': {
            'id': appointment.patient.id,
            'name': appointment.patient.full_name,
            'phone': appointment.patient.phone
        },
        'doctor': {
            'id': appointment.doctor.id,
            'name': appointment.doctor.full_name,
            'specialization': appointment.doctor.specialization
        },
        'appointment_date': appointment.appointment_date.isoformat(),
        'appointment_time': appointment.appointment_time.strftime('%H:%M'),
        'status': appointment.status,
        'reason': appointment.reason,
        'created_at': appointment.created_at.isoformat()
    }
    
    # Include treatment if completed
    if appointment.treatment:
        result['treatment'] = {
            'diagnosis': appointment.treatment.diagnosis,
            'prescription': appointment.treatment.prescription,
            'notes': appointment.treatment.notes,
            'follow_up_date': appointment.treatment.follow_up_date.isoformat() if appointment.treatment.follow_up_date else None
        }
    
    return jsonify({
        'success': True,
        'appointment': result
    })


@api_bp.route('/appointments', methods=['POST'])
@login_required
def create_appointment():
    """Create a new appointment (Patient only)"""
    if current_user.role != 'patient':
        return jsonify({'success': False, 'message': 'Only patients can book appointments'}), 403
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    data = request.get_json()
    
    required_fields = ['doctor_id', 'appointment_date', 'appointment_time']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    try:
        appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
        appointment_time = datetime.strptime(data['appointment_time'], '%H:%M').time()
        
        # Check for conflicts
        existing = Appointment.query.filter_by(
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='Booked'
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Time slot already booked'}), 400
        
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=data.get('reason', ''),
            status='Booked'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Appointment booked successfully',
            'appointment': {
                'id': appointment.id,
                'appointment_date': appointment.appointment_date.isoformat(),
                'appointment_time': appointment.appointment_time.strftime('%H:%M')
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def update_appointment(appointment_id):
    """Update appointment status"""
    appointment = Appointment.query.get_or_404(appointment_id)
    data = request.get_json()
    
    # Check authorization
    if current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        if appointment.doctor_id != doctor.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    elif current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if appointment.patient_id != patient.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    elif current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        if 'status' in data:
            appointment.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Appointment updated successfully',
            'appointment': {
                'id': appointment.id,
                'status': appointment.status
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
def cancel_appointment_api(appointment_id):
    """Cancel an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Check authorization
    if current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if appointment.patient_id != patient.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    elif current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if appointment.status != 'Booked':
        return jsonify({'success': False, 'message': 'Cannot cancel this appointment'}), 400
    
    try:
        appointment.status = 'Cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Appointment cancelled successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Departments API
@api_bp.route('/departments', methods=['GET'])
@login_required
def get_departments():
    """Get all departments"""
    departments = Department.query.all()
    
    return jsonify({
        'success': True,
        'count': len(departments),
        'departments': [{
            'id': dept.id,
            'name': dept.name,
            'description': dept.description,
            'doctor_count': len(dept.doctors)
        } for dept in departments]
    })


@api_bp.route('/departments/<int:department_id>', methods=['GET'])
@login_required
def get_department(department_id):
    """Get a specific department with its doctors"""
    department = Department.query.get_or_404(department_id)
    
    return jsonify({
        'success': True,
        'department': {
            'id': department.id,
            'name': department.name,
            'description': department.description,
            'doctors': [{
                'id': doc.id,
                'full_name': doc.full_name,
                'specialization': doc.specialization
            } for doc in department.doctors if doc.user.is_active]
        }
    })
