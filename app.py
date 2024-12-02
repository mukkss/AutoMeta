from flask import Flask, render_template, request, redirect, url_for, flash, session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess  # To run the attendance_taker.py script
import os  # For generating a new secret key on every restart
from dotenv import load_dotenv  # For loading environment variables from .env file

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a new secret key on each restart

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB URI if hosted
db = client["attendance_system"]  # Database name
users_collection = db["users"]  # Users collection
attendance_collection = db["attendance"]  # Attendance collection

@app.route('/')
def home():
    # If the user is already logged in, redirect to the index page
    if 'email' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role')
        department = request.form.get('department')
        semester = request.form.get('sem')
        subject = request.form.get('sub')
        phone = request.form.get('phone')
        emp_id = request.form.get('emp_id')

        # Check if user already exists
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return render_template('registration.html', error="Email already registered.")

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Save user to the database
        user_data = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'role': role,
            'department': department,
            'semester': semester,
            'subject': subject,
            'phone': phone,
            'emp_id': emp_id
        }
        users_collection.insert_one(user_data)

        # Redirect to login after successful registration
        return redirect(url_for('login'))

    return render_template('registration.html')  # Render the registration form

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Check if the email exists in the database
        user = users_collection.find_one({'email': email})
        if user:
            # Generate a unique password reset link (token can be a hashed value or UUID)
            reset_token = os.urandom(16).hex()
            
            # Save the token in the database for validation later
            users_collection.update_one(
                {'email': email},
                {'$set': {'reset_token': reset_token}}
            )
            
            # Create a password reset link
            reset_link = f"http://127.0.0.1:5000/reset_password/{reset_token}"
            
            # Use the send_reset_email function to send the email
            if send_reset_email(email, reset_link):
                flash("A password reset link has been sent to your email.", "success")
            else:
                flash("Failed to send the reset email. Please try again later.", "error")
        else:
            flash("Email not found.", "error")
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Verify the token
    user = users_collection.find_one({'reset_token': token})
    if not user:
        return "Invalid or expired token", 400

    if request.method == 'POST':
        new_password = request.form.get('password')
        
        # Hash the new password and update it in the database
        hashed_password = generate_password_hash(new_password)
        users_collection.update_one(
            {'reset_token': token},
            {'$set': {'password': hashed_password, 'reset_token': None}}  # Remove the token
        )
        
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Login route for handling user authentication
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Fetch user from the database
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            # Save email to the session to track the logged-in user
            session['email'] = email
            session['name'] = user['name']  # Optional: For personalized greetings
            return redirect(url_for('index'))
        
        return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    # Index page with options to take attendance or view attendance log
    if 'email' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    if request.method == 'POST':
        if 'take_attendance' in request.form:
            # Run the attendance_taker.py script
            subprocess.run(['python', 'attendance_taker.py'])
            return render_template('index.html', name=session.get('name', 'User'), message="Attendance process completed.")
        
        elif 'view_log' in request.form:
            # Redirect to the attendance log page
            return redirect(url_for('attendance_log'))
    
    return render_template('index.html', name=session.get('name', 'User'))  # Render the index page

@app.route('/attendance_log', methods=['GET', 'POST'])
def attendance_log():
    if 'email' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        # Get date and hour from form
        date = request.form.get('date')
        hour = request.form.get('hour')

        # Query the MongoDB database for records matching the date and hour, and sort by USN
        attendance_records = attendance_collection.find({
            "date": date,
            "hour": int(hour)
        }).sort("usn", 1)  # Sort by 'usn' in ascending order

        # Convert MongoDB Cursor to a List
        attendance_list = list(attendance_records)

        # Render the template with the fetched and sorted data
        return render_template('attendancelog.html', records=attendance_list)

    # Render the attendance log page with form initially
    return render_template('attendancelog.html', records=None)

@app.route('/logout')
def logout():
    # Clear session on logout and redirect to login
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)







