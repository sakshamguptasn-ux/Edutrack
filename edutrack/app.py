from flask import Flask, redirect, url_for, session
from config import Config
from db import close_db
import os
from datetime import datetime, date, timezone, timedelta


STATUS_BADGE_MAP = {
    'DRAFT': 'badge-draft',
    'UNDER_REVIEW': 'badge-under-review',
    'REVISION_REQUESTED': 'badge-revision',
    'APPROVED': 'badge-approved',
    'IN_PROGRESS': 'badge-in-progress',
    'COMPLETED': 'badge-completed',
    'OPEN': 'badge-open',
    'CLOSED': 'badge-closed',
    'PENDING': 'badge-pending',
    'SUBMITTED': 'badge-submitted',
    'REVIEWED': 'badge-reviewed',
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure directories exist
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register teardown
    app.teardown_appcontext(close_db)

    # Register Jinja2 template filters
    @app.template_filter('format_date')
    def format_date_filter(value):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
        if isinstance(value, (datetime, date)):
            return value.strftime('%b %d, %Y')
        return str(value)

    @app.template_filter('format_datetime')
    def format_datetime_filter(value):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
        if isinstance(value, (datetime, date)):
            # Convert SQLite UTC timestamps to IST (UTC+5:30)
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    utc_dt = value.replace(tzinfo=timezone.utc)
                    local_dt = utc_dt.astimezone(ist_tz)
                else:
                    local_dt = value.astimezone(ist_tz)
                return local_dt.strftime('%b %d, %Y %I:%M %p')
            return value.strftime('%b %d, %Y')
        return str(value)

    @app.template_filter('status_display')
    def status_display_filter(value):
        if value is None:
            return ''
        return value.replace('_', ' ').title()

    @app.template_filter('status_class')
    def status_class_filter(value):
        if value is None:
            return ''
        return STATUS_BADGE_MAP.get(value, 'badge-secondary')

    @app.template_filter('deadline_class')
    def deadline_class_filter(value):
        if value is None:
            return 'badge-upcoming', 'Upcoming'
        try:
            if isinstance(value, str):
                due = datetime.strptime(value, '%Y-%m-%d').date()
            elif isinstance(value, datetime):
                due = value.date()
            elif isinstance(value, date):
                due = value
            else:
                return 'badge-upcoming', 'Upcoming'
            today = date.today()
            delta = (due - today).days
            if delta < 0:
                return 'badge-overdue', 'Overdue'
            elif delta <= 3:
                return 'badge-due-soon', 'Due Soon'
            else:
                return 'badge-upcoming', 'Upcoming'
        except (ValueError, TypeError):
            return 'badge-upcoming', 'Upcoming'

    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}

    # Register blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.faculty import faculty_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(faculty_bp, url_prefix='/faculty')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Index redirect
    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('role')
            if role == 'student':
                return redirect(url_for('student.dashboard'))
            elif role == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin.dashboard'))
        return redirect(url_for('auth.login'))

    # Custom error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return '''<div style="text-align:center;margin-top:100px;font-family:sans-serif;">
            <h1>403 — Forbidden</h1><p>You do not have permission to access this page.</p>
            <a href="/">Go Home</a></div>''', 403

    @app.errorhandler(404)
    def not_found(e):
        return '''<div style="text-align:center;margin-top:100px;font-family:sans-serif;">
            <h1>404 — Not Found</h1><p>The page you are looking for does not exist.</p>
            <a href="/">Go Home</a></div>''', 404

    return app


if __name__ == '__main__':
    app = create_app()
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug_mode, port=5000)
