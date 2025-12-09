from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from models import User, Patient
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Home route - redirects based on user role
@auth_bp.route('/')
def index():
    userIsLoggedIn = current_user.is_authenticated
    
    if userIsLoggedIn:
        userRole = current_user.role
        
        # Using dictionary for routing 
        dashboardRoutes = {
            'admin': 'admin.dashboard',
            'doctor': 'doctor.dashboard',
            'patient': 'patient.dashboard'
        }
        
        if userRole in dashboardRoutes:
            targetRoute = dashboardRoutes[userRole]
            return redirect(url_for(targetRoute))
    
    # Not logged in, show landing page
    return render_template('index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    requestMethod = request.method
    if requestMethod == 'POST':
        inputUsername = request.form.get('username', '').strip()
        inputPassword = request.form.get('password', '').strip()
        
        # Basic validation - both fields required
        fieldsAreEmpty = (not inputUsername or not inputPassword)
        if fieldsAreEmpty:
            flash('Please enter both username and password.', 'danger')
            return render_template('auth/login.html')
        
        # Try to find user in database
        foundUser = User.query.filter_by(username=inputUsername).first()
        
        if foundUser is not None:
            passwordIsCorrect = foundUser.check_password(inputPassword)
            
            if passwordIsCorrect:
                accountActive = foundUser.is_active
                if not accountActive:
                    flash('Your account has been deactivated. Please contact admin.', 'danger')
                    return render_template('auth/login.html')
                
                # All good, log them in
                login_user(foundUser)
                
                # Check for redirect parameter
                nextPage = request.args.get('next')
                if nextPage:
                    return redirect(nextPage)
                
                # Redirect based on role
                userRole = foundUser.role
                if userRole == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif userRole == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                elif userRole == 'patient':
                    return redirect(url_for('patient.dashboard'))
                else:
                    # Fallback just in case
                    return redirect(url_for('auth.index'))
            else:
                # Wrong password
                flash('Invalid username or password.', 'danger')
        else:
            # User not found
            flash('Invalid username or password.', 'danger')
    
    # GET request or login failed, show form
    return render_template('auth/login.html')


# Patient registration route - only for new patients
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Already logged in? Redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    # Handle form submission
    if request.method == 'POST':
        # Collect all form data - lots of fields!
        formUsername = request.form.get('username', '').strip()
        formEmail = request.form.get('email', '').strip()
        formPassword = request.form.get('password', '').strip()
        confirmPassword = request.form.get('confirm_password', '').strip()
        fullName = request.form.get('full_name', '').strip()
        phoneNumber = request.form.get('phone', '').strip()
        dateOfBirth = request.form.get('date_of_birth', '').strip()
        patientGender = request.form.get('gender', '').strip()
        patientAddress = request.form.get('address', '').strip()
        bloodGroup = request.form.get('blood_group', '').strip()
        emergencyContact = request.form.get('emergency_contact', '').strip()
        
        if not all([formUsername, formEmail, formPassword, confirmPassword, fullName, phoneNumber]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register.html')
        
        
        passwordsMatch = (formPassword == confirmPassword)
        if not passwordsMatch:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        
        
        passwordLength = len(formPassword)
        if passwordLength < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')
        
        
        existingUser = User.query.filter_by(username=formUsername).first()
        if existingUser is not None:
            flash('Username already exists.', 'danger')
            return render_template('auth/register.html')
        
        existingEmail = User.query.filter_by(email=formEmail).first()
        if existingEmail:
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')
        
        try:
            newUser = User(
                username=formUsername,
                email=formEmail,
                role='patient'
            )
            newUser.set_password(formPassword)
            db.session.add(newUser)
            db.session.flush()
            
            # Parse date of birth if provided
            parsedDob = None
            if dateOfBirth:
                try:
                    parsedDob = datetime.strptime(dateOfBirth, '%Y-%m-%d').date()
                except:
                    parsedDob = None  # Invalid date format, ignore
            
            # Create patient profile
            newPatient = Patient(
                user_id=newUser.id,
                full_name=fullName,
                phone=phoneNumber,
                date_of_birth=parsedDob,
                gender=patientGender,
                address=patientAddress,
                blood_group=bloodGroup,
                emergency_contact=emergencyContact
            )
            db.session.add(newPatient)
            db.session.commit()  # Save everything
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as registrationError:
            # kuch hua toh rollback kar do 
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            print(f"Registration error: {registrationError}")  # For debugging
    
    # GET request, show registration form
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.index'))
