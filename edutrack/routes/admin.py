from flask import Blueprint, render_template, redirect, url_for, flash, request, session
import re
from werkzeug.security import generate_password_hash
from db import get_db, query_db
from routes import role_required

admin_bp = Blueprint('admin', __name__, template_folder='../templates')


# ── Dashboard ───────────────────────────────────────────────

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    users_total = query_db("SELECT COUNT(*) AS c FROM users", one=True)['c']
    students_total = query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'student'", one=True)['c']
    faculty_total = query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'faculty'", one=True)['c']
    admins_total = query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'", one=True)['c']

    assignments_total = query_db("SELECT COUNT(*) AS c FROM assignments", one=True)['c']
    projects_total = query_db("SELECT COUNT(*) AS c FROM projects", one=True)['c']
    completed_projects = query_db("SELECT COUNT(*) AS c FROM projects WHERE status = 'COMPLETED'", one=True)['c']
    pending_projects = query_db("SELECT COUNT(*) AS c FROM projects WHERE status = 'UNDER_REVIEW'", one=True)['c']

    projects_by_status = query_db("SELECT status, COUNT(*) AS c FROM projects GROUP BY status")

    recent_projects = query_db(
        "SELECT project_id, title, status, updated_at FROM projects ORDER BY updated_at DESC LIMIT 5"
    )

    return render_template(
        'admin/dashboard.html',
        users_total=users_total, students_total=students_total,
        faculty_total=faculty_total, admins_total=admins_total,
        assignments_total=assignments_total, projects_total=projects_total,
        completed_projects=completed_projects, pending_projects=pending_projects,
        projects_by_status=projects_by_status, recent_projects=recent_projects
    )


# ── User Management ────────────────────────────────────────

@admin_bp.route('/users')
@role_required('admin')
def users():
    q = request.args.get('q', '')
    role_filter = request.args.get('role', '')

    sql = "SELECT user_id, name, email, role, is_active, created_at FROM users WHERE 1=1"
    params = []

    if q:
        sql += " AND (name LIKE ? OR email LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    if role_filter:
        sql += " AND role = ?"
        params.append(role_filter)

    sql += " ORDER BY created_at DESC"
    all_users = query_db(sql, params)
    return render_template('admin/users.html', users=all_users,
                           q=q, role_filter=role_filter)


@admin_bp.route('/user/create', methods=['GET', 'POST'])
@role_required('admin')
def user_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')

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
        if role not in ('student', 'faculty', 'admin'):
            errors.append('Invalid role.')

        if not errors:
            existing = query_db('SELECT user_id FROM users WHERE email = ?',
                                [email], one=True)
            if existing:
                errors.append('An account with this email already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/user_create.html')

        db = get_db()
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, 1)',
            [name, email, generate_password_hash(password), role]
        )
        db.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_create.html')


@admin_bp.route('/user/<int:user_id>/toggle-active', methods=['POST'])
@role_required('admin')
def toggle_user_active(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users'))

    user = query_db('SELECT user_id, is_active FROM users WHERE user_id = ?',
                     [user_id], one=True)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.users'))

    new_status = 0 if user['is_active'] else 1
    db = get_db()
    db.execute('UPDATE users SET is_active = ? WHERE user_id = ?',
               [new_status, user_id])
    db.commit()

    action = 'activated' if new_status else 'deactivated'
    flash(f'User {action} successfully.', 'success')
    return redirect(url_for('admin.users'))


# ── Assignments ─────────────────────────────────────────────

@admin_bp.route('/assignments')
@role_required('admin')
def assignments():
    q = request.args.get('q', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT a.*, u.name AS faculty_name,
               (SELECT COUNT(*) FROM projects WHERE assignment_id = a.assignment_id) AS projects_count
        FROM assignments a
        JOIN users u ON a.faculty_id = u.user_id
        WHERE 1=1
    '''
    params = []
    if q:
        sql += ' AND a.title LIKE ?'
        params.append(f'%{q}%')
    if status_filter:
        sql += ' AND a.status = ?'
        params.append(status_filter)

    sql += ' ORDER BY a.created_at DESC'
    assigns = query_db(sql, params)
    return render_template('admin/assignments.html',
                           assignments=assigns, q=q, status_filter=status_filter)


@admin_bp.route('/assignment/<int:assignment_id>')
@role_required('admin')
def assignment_detail(assignment_id):
    assignment = query_db('''
        SELECT a.*, u.name AS faculty_name
        FROM assignments a JOIN users u ON a.faculty_id = u.user_id
        WHERE a.assignment_id = ?
    ''', [assignment_id], one=True)

    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('admin.assignments'))

    projects = query_db('''
        SELECT p.*, t.team_name
        FROM projects p JOIN teams t ON p.team_id = t.team_id
        WHERE p.assignment_id = ?
    ''', [assignment_id])

    return render_template('admin/assignment_detail.html',
                           assignment=assignment, projects=projects)


@admin_bp.route('/assignment/<int:assignment_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_assignment_status(assignment_id):
    assignment = query_db('SELECT * FROM assignments WHERE assignment_id = ?',
                          [assignment_id], one=True)
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('admin.assignments'))

    new_status = 'CLOSED' if assignment['status'] == 'OPEN' else 'OPEN'
    db = get_db()
    db.execute(
        'UPDATE assignments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE assignment_id = ?',
        [new_status, assignment_id]
    )
    db.commit()
    flash(f'Assignment status changed to {new_status}.', 'success')
    return redirect(url_for('admin.assignment_detail', assignment_id=assignment_id))


# ── Projects ────────────────────────────────────────────────

@admin_bp.route('/projects')
@role_required('admin')
def projects():
    q = request.args.get('q', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT p.*, a.title AS assignment_title, t.team_name, u.name AS faculty_name
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        JOIN teams t ON p.team_id = t.team_id
        JOIN users u ON p.faculty_id = u.user_id
        WHERE 1=1
    '''
    params = []
    if q:
        sql += ' AND p.title LIKE ?'
        params.append(f'%{q}%')
    if status_filter:
        sql += ' AND p.status = ?'
        params.append(status_filter)

    sql += ' ORDER BY p.updated_at DESC'
    projs = query_db(sql, params)
    return render_template('admin/projects.html',
                           projects=projs, q=q, status_filter=status_filter)


@admin_bp.route('/project/<int:project_id>')
@role_required('admin')
def project_detail(project_id):
    project = query_db('''
        SELECT p.*, a.title AS assignment_title, t.team_name, u.name AS faculty_name
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        JOIN teams t ON p.team_id = t.team_id
        JOIN users u ON p.faculty_id = u.user_id
        WHERE p.project_id = ?
    ''', [project_id], one=True)

    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('admin.projects'))

    team_members = query_db('''
        SELECT u.name, u.email
        FROM users u JOIN team_members tm ON u.user_id = tm.student_id
        WHERE tm.team_id = ?
    ''', [project['team_id']])

    reviews = query_db('''
        SELECT pr.*, u.name AS faculty_name
        FROM proposal_reviews pr JOIN users u ON pr.faculty_id = u.user_id
        WHERE pr.project_id = ? ORDER BY pr.created_at ASC
    ''', [project_id])

    milestones = query_db(
        'SELECT * FROM milestones WHERE project_id = ? ORDER BY due_date ASC',
        [project_id]
    )

    submissions = query_db('''
        SELECT s.*, m.title AS milestone_title, u.name AS student_name
        FROM submissions s
        LEFT JOIN milestones m ON s.milestone_id = m.milestone_id
        JOIN users u ON s.submitted_by = u.user_id
        WHERE s.project_id = ?
        ORDER BY s.submitted_at DESC
    ''', [project_id])

    evaluation = query_db(
        'SELECT e.*, u.name AS faculty_name FROM evaluations e '
        'JOIN users u ON e.faculty_id = u.user_id WHERE e.project_id = ?',
        [project_id], one=True
    )

    return render_template(
        'admin/project_detail.html',
        project=project, team_members=team_members, reviews=reviews,
        milestones=milestones, submissions=submissions, evaluation=evaluation
    )


# ── Reports ─────────────────────────────────────────────────

@admin_bp.route('/reports')
@role_required('admin')
def reports():
    projects_by_status = query_db(
        "SELECT status, COUNT(*) AS c FROM projects GROUP BY status"
    )

    assignments_total = query_db("SELECT COUNT(*) AS c FROM assignments", one=True)['c']
    assignments_open = query_db("SELECT COUNT(*) AS c FROM assignments WHERE status = 'OPEN'", one=True)['c']
    assignments_closed = query_db("SELECT COUNT(*) AS c FROM assignments WHERE status = 'CLOSED'", one=True)['c']

    completed_with_grades = query_db('''
        SELECT p.title AS project_title, t.team_name, u.name AS faculty_name,
               e.grade, e.comments, e.evaluated_at
        FROM evaluations e
        JOIN projects p ON e.project_id = p.project_id
        JOIN teams t ON p.team_id = t.team_id
        JOIN users u ON e.faculty_id = u.user_id
        ORDER BY e.evaluated_at DESC
    ''')

    return render_template(
        'admin/reports.html',
        projects_by_status=projects_by_status,
        assignments_total=assignments_total,
        assignments_open=assignments_open,
        assignments_closed=assignments_closed,
        completed_with_grades=completed_with_grades
    )
