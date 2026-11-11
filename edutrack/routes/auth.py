import re
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, query_db
from routes import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.app_context_processor
def inject_unread_count():
    """Inject unread notification count into all templates."""
    if 'user_id' in session:
        count = query_db(
            'SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND is_read = 0',
            [session['user_id']], one=True
        )
        return {'unread_count': count['cnt'] if count else 0}
    return {'unread_count': 0}


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')

        user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)

        if user is None:
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        if not user['is_active']:
            flash('Your account has been deactivated. Please contact the administrator.', 'danger')
            return render_template('login.html')

        if not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        session.clear()
        session['user_id'] = user['user_id']
        session['user_name'] = user['name']
        session['role'] = user['role']

        flash(f'Welcome back, {user["name"]}!', 'success')

        if user['role'] == 'student':
            return redirect(url_for('student.dashboard'))
        elif user['role'] == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')
        faculty_passcode = request.form.get('faculty_passcode', '').strip()

        errors = []

        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append('Please enter a valid email address.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if role not in ('student', 'faculty'):
            errors.append('Invalid role selected.')

        # Validate faculty passcode
        if role == 'faculty':
            if not faculty_passcode:
                errors.append('Faculty Authorization Code is required to register as Faculty.')
            elif faculty_passcode != current_app.config['FACULTY_PASSCODE']:
                errors.append('Invalid Faculty Authorization Code. Please contact your administrator.')

        if not errors:
            existing = query_db('SELECT user_id FROM users WHERE email = ?', [email], one=True)
            if existing:
                errors.append('An account with this email already exists.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        db = get_db()
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            [name, email, generate_password_hash(password), role, 1]
        )
        db.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/download/<filename>')
@login_required
def download_file(filename):
    """Serve uploaded files for authorized users."""
    import os
    upload_folder = current_app.config['UPLOAD_FOLDER']
    filepath = os.path.join(upload_folder, filename)
    if not os.path.exists(filepath):
        flash('File not found.', 'danger')
        return redirect(request.referrer or url_for('index'))
    return send_from_directory(upload_folder, filename, as_attachment=True)
