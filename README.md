# Hospital Management System

A comprehensive web-based Hospital Management System built with Flask that allows Admins, Doctors, and Patients to interact with the system based on their roles.

## Features

### Admin Features
- Dashboard with statistics (total doctors, patients, appointments)
- Add, update, and delete doctor profiles
- Manage patient information
- View and manage all appointments
- Search for patients and doctors

### Doctor Features
- Dashboard showing today's and week's appointments
- View assigned appointments
- Mark appointments as completed
- Add diagnosis, prescriptions, and treatment notes
- View patient history
- Manage availability for next 7 days

### Patient Features
- Register and login
- Dashboard with departments and specializations
- Search for doctors by specialization
- View doctor profiles and availability
- Book appointments with available doctors
- View appointment history
- Cancel booked appointments
- View medical history with diagnoses and prescriptions

### Additional Features
- RESTful API endpoints for all major operations
- Frontend validation using HTML5
- Backend validation in controllers
- Responsive design with Bootstrap 5
- Secure authentication with Flask-Login
- Prevents appointment conflicts
- Dynamic appointment status updates

## Technology Stack

- **Backend**: Flask 2.3.3
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, Bootstrap 5, Jinja2
- **Authentication**: Flask-Login
- **ORM**: Flask-SQLAlchemy

## Project Structure

```
hospital_management_system/
├── app.py                  # Main application file
├── config.py              # Configuration settings
├── models.py              # Database models
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── routes/
│   ├── auth.py           # Authentication routes
│   ├── admin.py          # Admin routes
│   ├── doctor.py         # Doctor routes
│   ├── patient.py        # Patient routes
│   └── api.py            # API endpoints
└── templates/
    ├── base.html         # Base template
    ├── index.html        # Home page
    ├── auth/             # Authentication templates
    ├── admin/            # Admin templates
    ├── doctor/           # Doctor templates
    └── patient/          # Patient templates
```

## Installation

1. **Clone or extract the project**

2. **Create a virtual environment** (recommended):
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

3. **Install dependencies**:
```powershell
pip install -r requirements.txt
```

4. **Run the application**:
```powershell
python app.py
```

5. **Access the application**:
Open your browser and navigate to `http://127.0.0.1:5000/`

## Database

The database is created automatically when you run the application for the first time. The following tables are created:

- **users** - User accounts (Admin, Doctor, Patient)
- **departments** - Medical departments
- **doctors** - Doctor profiles
- **patients** - Patient profiles
- **appointments** - Appointment records
- **treatments** - Treatment details
- **doctor_availability** - Doctor availability slots

## Default Login Credentials

### Admin
- Username: `admin`
- Password: `admin123`

### Test Accounts
After first run, you can:
- Register as a Patient directly
- Admin can add Doctor accounts

## API Endpoints

The system provides RESTful API endpoints:

### Doctors
- GET `/api/doctors` - Get all doctors
- GET `/api/doctors/<id>` - Get specific doctor
- PUT `/api/doctors/<id>` - Update doctor (Admin only)
- DELETE `/api/doctors/<id>` - Deactivate doctor (Admin only)

### Patients
- GET `/api/patients` - Get all patients (Admin only)
- GET `/api/patients/<id>` - Get specific patient

### Appointments
- GET `/api/appointments` - Get appointments (role-based)
- GET `/api/appointments/<id>` - Get specific appointment
- POST `/api/appointments` - Create appointment (Patient only)
- PUT `/api/appointments/<id>` - Update appointment
- DELETE `/api/appointments/<id>` - Cancel appointment

### Departments
- GET `/api/departments` - Get all departments
- GET `/api/departments/<id>` - Get specific department with doctors

## Key Features Implemented

1. **Role-based Access Control**: Different dashboards and permissions for Admin, Doctor, and Patient
2. **Appointment Management**: Full CRUD operations with conflict prevention
3. **Doctor Availability**: Doctors can set their availability for the next 7 days
4. **Treatment Records**: Complete medical history tracking
5. **Search Functionality**: Search doctors by name/specialization, search patients by name/phone/ID
6. **Professional UI**: Clean, responsive design using Bootstrap 5
7. **Form Validation**: Both frontend (HTML5) and backend validation
8. **API Support**: RESTful API for external integrations

## Usage Guide

### For Patients:
1. Register a new account
2. Browse available departments
3. Search for doctors by specialization
4. View doctor profiles and availability
5. Book appointments
6. View your appointment history
7. Access your medical records

### For Doctors:
1. Login with credentials (provided by admin)
2. View today's appointments
3. Set your availability
4. Complete appointments with diagnosis and prescriptions
5. View patient histories

### For Admins:
1. Login with admin credentials
2. Add/manage doctors
3. View/manage all patients
4. Monitor all appointments
5. Search and view detailed records

## Security Notes

- Change the default admin password after first login
- Update the SECRET_KEY in config.py for production use
- Passwords are hashed using Werkzeug's security functions
- Role-based decorators prevent unauthorized access

## Development Notes

- Database is created programmatically (no manual DB creation needed)
- Admin user is auto-created on first run
- Default departments are seeded automatically
- All timestamps use UTC

## Troubleshooting

If you encounter any issues:

1. **Import Errors**: Make sure all dependencies are installed
```powershell
pip install -r requirements.txt
```

2. **Database Errors**: Delete `hospital.db` and restart the application to recreate the database

3. **Port Already in Use**: Change the port in `app.py`:
```python
app.run(debug=True, port=5001)
```

## Future Enhancements

- Email notifications for appointments
- PDF generation for prescriptions
- Appointment reminders
- Doctor reviews and ratings
- Advanced search filters
- Analytics dashboard
- Export patient records

## License

This project is created for educational purposes as part of the MAD-1 course.

## Contact

For any queries or issues, please refer to the project documentation or contact the development team.
