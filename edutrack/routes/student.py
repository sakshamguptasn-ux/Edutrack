import os
import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app
)
from werkzeug.utils import secure_filename
from db import get_db, query_db
from routes import role_required

student_bp = Blueprint('student', __name__, template_folder='../templates')


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


# ── Dashboard ───────────────────────────────────────────────

@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    uid = session['user_id']

    teams = query_db('''
        SELECT t.* FROM teams t
        JOIN team_members tm ON t.team_id = tm.team_id
        WHERE tm.student_id = ?
    ''', [uid])

    projects = query_db('''
        SELECT p.*, a.title AS assignment_title
        FROM projects p
        JOIN team_members tm ON p.team_id = tm.team_id
        JOIN assignments a ON p.assignment_id = a.assignment_id
        WHERE tm.student_id = ?
    ''', [uid])

    milestones = query_db('''
        SELECT m.*, p.title AS project_title, p.project_id
        FROM milestones m
        JOIN projects p ON m.project_id = p.project_id
        JOIN team_members tm ON p.team_id = tm.team_id
        WHERE tm.student_id = ? AND m.status != 'COMPLETED'
        ORDER BY m.due_date ASC
    ''', [uid])

    feedbacks = query_db('''
        SELECT f.*, s.original_filename AS submission_name
        FROM feedback f
        JOIN submissions s ON f.submission_id = s.submission_id
        JOIN projects p ON s.project_id = p.project_id
        JOIN team_members tm ON p.team_id = tm.team_id
        WHERE tm.student_id = ?
        ORDER BY f.created_at DESC LIMIT 5
    ''', [uid])

    unread_notifications = query_db('''
        SELECT * FROM notifications
        WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC
    ''', [uid])

    open_assignments = query_db(
        "SELECT COUNT(*) AS count FROM assignments WHERE status = 'OPEN'",
        one=True
    )['count']

    return render_template(
        'student/dashboard.html',
        teams=teams, projects=projects, milestones=milestones,
        feedbacks=feedbacks, unread_notifications=unread_notifications,
        open_assignments=open_assignments
    )


# ── Assignments ─────────────────────────────────────────────

@student_bp.route('/assignments')
@role_required('student')
def assignments():
    q = request.args.get('q', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT a.*, u.name AS faculty_name
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

    sql += ' ORDER BY a.deadline ASC'
    assigns = query_db(sql, params)
    return render_template('student/assignments.html',
                           assignments=assigns, q=q, status_filter=status_filter)


@student_bp.route('/assignment/<int:assignment_id>')
@role_required('student')
def assignment_detail(assignment_id):
    assignment = query_db('''
        SELECT a.*, u.name AS faculty_name
        FROM assignments a
        JOIN users u ON a.faculty_id = u.user_id
        WHERE a.assignment_id = ?
    ''', [assignment_id], one=True)

    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('student.assignments'))

    project = query_db('''
        SELECT p.*
        FROM projects p
        JOIN team_members tm ON p.team_id = tm.team_id
        WHERE p.assignment_id = ? AND tm.student_id = ?
    ''', [assignment_id, session['user_id']], one=True)

    return render_template('student/assignment_detail.html',
                           assignment=assignment, project=project)


# ── Teams ───────────────────────────────────────────────────

@student_bp.route('/teams')
@role_required('student')
def teams():
    uid = session['user_id']
    teams_data = query_db('''
        SELECT t.*,
               (SELECT COUNT(*) FROM team_members WHERE team_id = t.team_id) AS member_count,
               (SELECT COUNT(*) FROM projects WHERE team_id = t.team_id) AS project_count
        FROM teams t
        JOIN team_members tm ON t.team_id = tm.team_id
        WHERE tm.student_id = ?
    ''', [uid])
    return render_template('student/teams.html', teams=teams_data)


@student_bp.route('/team/create', methods=['GET', 'POST'])
@role_required('student')
def team_create():
    if request.method == 'POST':
        name = request.form.get('team_name', '').strip()
        if not name:
            flash('Team name is required.', 'danger')
        else:
            db = get_db()
            cur = db.execute(
                'INSERT INTO teams (team_name, created_by) VALUES (?, ?)',
                [name, session['user_id']]
            )
            team_id = cur.lastrowid
            db.execute(
                'INSERT INTO team_members (team_id, student_id) VALUES (?, ?)',
                [team_id, session['user_id']]
            )
            db.commit()
            flash('Team created successfully.', 'success')
            return redirect(url_for('student.team_detail', team_id=team_id))
    return render_template('student/team_create.html')


@student_bp.route('/team/<int:team_id>')
@role_required('student')
def team_detail(team_id):
    uid = session['user_id']
    membership = query_db(
        'SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
        [team_id, uid], one=True
    )
    if not membership:
        flash('You are not a member of this team.', 'danger')
        return redirect(url_for('student.teams'))

    team = query_db('SELECT * FROM teams WHERE team_id = ?', [team_id], one=True)
    members = query_db('''
        SELECT u.user_id, u.name, u.email
        FROM users u
        JOIN team_members tm ON u.user_id = tm.student_id
        WHERE tm.team_id = ?
    ''', [team_id])

    projects = query_db('''
        SELECT p.*, a.title AS assignment_title
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        WHERE p.team_id = ?
    ''', [team_id])

    return render_template('student/team_detail.html',
                           team=team, members=members, projects=projects)


@student_bp.route('/team/<int:team_id>/add-member', methods=['POST'])
@role_required('student')
def team_add_member(team_id):
    uid = session['user_id']
    membership = query_db(
        'SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
        [team_id, uid], one=True
    )
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.teams'))

    email = request.form.get('email', '').strip()
    if not email:
        flash('Email is required.', 'danger')
        return redirect(url_for('student.team_detail', team_id=team_id))

    user = query_db(
        "SELECT * FROM users WHERE email = ? AND role = 'student' AND is_active = 1",
        [email], one=True
    )
    if not user:
        flash('Student not found or inactive.', 'danger')
    else:
        existing = query_db(
            'SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
            [team_id, user['user_id']], one=True
        )
        if existing:
            flash('User is already a member of this team.', 'warning')
        else:
            db = get_db()
            db.execute(
                'INSERT INTO team_members (team_id, student_id) VALUES (?, ?)',
                [team_id, user['user_id']]
            )
            db.commit()
            flash(f'{user["name"]} added to the team.', 'success')

    return redirect(url_for('student.team_detail', team_id=team_id))


# ── Project Creation ────────────────────────────────────────

@student_bp.route('/project/create/<int:assignment_id>', methods=['GET', 'POST'])
@role_required('student')
def project_create(assignment_id):
    assignment = query_db(
        "SELECT * FROM assignments WHERE assignment_id = ? AND status = 'OPEN'",
        [assignment_id], one=True
    )
    if not assignment:
        flash('Assignment not found or closed.', 'danger')
        return redirect(url_for('student.assignments'))

    uid = session['user_id']
    my_teams = query_db('''
        SELECT t.* FROM teams t
        JOIN team_members tm ON t.team_id = tm.team_id
        WHERE tm.student_id = ?
    ''', [uid])

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        team_id = request.form.get('team_id')

        if not title or not team_id:
            flash('Title and Team are required.', 'danger')
            return render_template('student/project_create.html',
                                   assignment=assignment, teams=my_teams)

        # Verify membership
        is_member = any(str(t['team_id']) == str(team_id) for t in my_teams)
        if not is_member:
            flash('Invalid team selection.', 'danger')
            return render_template('student/project_create.html',
                                   assignment=assignment, teams=my_teams)

        # Check duplicate
        existing = query_db(
            'SELECT * FROM projects WHERE assignment_id = ? AND team_id = ?',
            [assignment_id, team_id], one=True
        )
        if existing:
            flash('This team already has a project for this assignment.', 'warning')
            return render_template('student/project_create.html',
                                   assignment=assignment, teams=my_teams)

        db = get_db()
        cur = db.execute('''
            INSERT INTO projects (assignment_id, team_id, faculty_id, title, description, status)
            VALUES (?, ?, ?, ?, ?, 'DRAFT')
        ''', [assignment_id, team_id, assignment['faculty_id'], title, description])
        project_id = cur.lastrowid
        db.commit()
        flash('Project created successfully.', 'success')
        return redirect(url_for('student.project_detail', project_id=project_id))

    return render_template('student/project_create.html',
                           assignment=assignment, teams=my_teams)


# ── Project Detail ──────────────────────────────────────────

@student_bp.route('/project/<int:project_id>')
@role_required('student')
def project_detail(project_id):
    uid = session['user_id']

    project = query_db('''
        SELECT p.*, a.title AS assignment_title, t.team_name,
               u.name AS faculty_name
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        JOIN teams t ON p.team_id = t.team_id
        JOIN users u ON p.faculty_id = u.user_id
        WHERE p.project_id = ?
    ''', [project_id], one=True)

    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    membership = query_db(
        'SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
        [project['team_id'], uid], one=True
    )
    if not membership:
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    reviews = query_db(
        'SELECT pr.*, u.name AS faculty_name FROM proposal_reviews pr '
        'JOIN users u ON pr.faculty_id = u.user_id '
        'WHERE pr.project_id = ? ORDER BY pr.created_at ASC',
        [project_id]
    )
    milestones = query_db(
        'SELECT * FROM milestones WHERE project_id = ? ORDER BY due_date ASC',
        [project_id]
    )
    submissions = query_db(
        'SELECT s.*, m.title AS milestone_title '
        'FROM submissions s '
        'LEFT JOIN milestones m ON s.milestone_id = m.milestone_id '
        'WHERE s.project_id = ?',
        [project_id]
    )
    feedbacks = query_db('''
        SELECT f.*, s.original_filename AS submission_name, u.name AS faculty_name
        FROM feedback f
        JOIN submissions s ON f.submission_id = s.submission_id
        JOIN users u ON f.faculty_id = u.user_id
        WHERE s.project_id = ?
        ORDER BY f.created_at DESC
    ''', [project_id])

    evaluation = query_db(
        'SELECT e.*, u.name AS faculty_name FROM evaluations e '
        'JOIN users u ON e.faculty_id = u.user_id '
        'WHERE e.project_id = ?',
        [project_id], one=True
    )

    return render_template(
        'student/project_detail.html',
        project=project, reviews=reviews, milestones=milestones,
        submissions=submissions, feedbacks=feedbacks, evaluation=evaluation
    )


# ── Proposal Submit / Resubmit ──────────────────────────────

@student_bp.route('/project/<int:project_id>/submit-proposal', methods=['POST'])
@role_required('student')
def submit_proposal(project_id):
    uid = session['user_id']
    project = query_db('SELECT * FROM projects WHERE project_id = ?',
                       [project_id], one=True)
    if not project or project['status'] != 'DRAFT':
        flash('Invalid action.', 'danger')
        return redirect(url_for('student.dashboard'))

    if not query_db('SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
                    [project['team_id'], uid], one=True):
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    db = get_db()
    db.execute(
        "UPDATE projects SET status = 'UNDER_REVIEW', submitted_at = CURRENT_TIMESTAMP, "
        "updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
        [project_id]
    )
    db.execute(
        "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
        "VALUES (?, ?, 'proposal_submitted', ?)",
        [project['faculty_id'],
         f"New proposal submitted for project: {project['title']}",
         project_id]
    )
    db.commit()
    flash('Proposal submitted successfully.', 'success')
    return redirect(url_for('student.project_detail', project_id=project_id))


@student_bp.route('/project/<int:project_id>/resubmit-proposal', methods=['POST'])
@role_required('student')
def resubmit_proposal(project_id):
    uid = session['user_id']
    project = query_db('SELECT * FROM projects WHERE project_id = ?',
                       [project_id], one=True)
    if not project or project['status'] != 'REVISION_REQUESTED':
        flash('Invalid action.', 'danger')
        return redirect(url_for('student.dashboard'))

    if not query_db('SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
                    [project['team_id'], uid], one=True):
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    db = get_db()
    db.execute(
        "UPDATE projects SET status = 'UNDER_REVIEW', updated_at = CURRENT_TIMESTAMP "
        "WHERE project_id = ?",
        [project_id]
    )
    db.execute(
        "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
        "VALUES (?, ?, 'proposal_resubmitted', ?)",
        [project['faculty_id'],
         f"Proposal resubmitted for project: {project['title']}",
         project_id]
    )
    db.commit()
    flash('Proposal resubmitted successfully.', 'success')
    return redirect(url_for('student.project_detail', project_id=project_id))


# ── Milestone Submission ────────────────────────────────────

@student_bp.route('/project/<int:project_id>/milestone/<int:milestone_id>/submit',
                  methods=['GET', 'POST'])
@role_required('student')
def milestone_submit(project_id, milestone_id):
    uid = session['user_id']
    project = query_db('SELECT * FROM projects WHERE project_id = ?',
                       [project_id], one=True)
    milestone = query_db(
        'SELECT * FROM milestones WHERE milestone_id = ? AND project_id = ?',
        [milestone_id, project_id], one=True
    )

    if not project or not milestone:
        flash('Not found.', 'danger')
        return redirect(url_for('student.dashboard'))

    if not query_db('SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
                    [project['team_id'], uid], one=True):
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        file = request.files.get('file')
        desc = request.form.get('description', '').strip()

        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('File type not allowed. Allowed: PDF, DOC, DOCX, PPT, PPTX.', 'danger')
            return redirect(request.url)

        original_filename = secure_filename(file.filename)
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(upload_path)

        db = get_db()
        db.execute('''
            INSERT INTO submissions
                (project_id, milestone_id, submitted_by, original_filename,
                 stored_filename, file_path, description, submission_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'MILESTONE', 'SUBMITTED')
        ''', [project_id, milestone_id, uid, original_filename,
              stored_filename, upload_path, desc])

        db.execute(
            "UPDATE milestones SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP "
            "WHERE milestone_id = ?",
            [milestone_id]
        )

        db.execute(
            "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
            "VALUES (?, ?, 'milestone_submitted', ?)",
            [project['faculty_id'],
             f"New milestone submission for '{milestone['title']}' in project: {project['title']}",
             project_id]
        )
        db.commit()
        flash('Milestone submitted successfully.', 'success')
        return redirect(url_for('student.project_detail', project_id=project_id))

    return render_template('student/milestone_submit.html',
                           project=project, milestone=milestone)


# ── Final Submission ────────────────────────────────────────

@student_bp.route('/project/<int:project_id>/final-submit', methods=['GET', 'POST'])
@role_required('student')
def final_submit(project_id):
    uid = session['user_id']
    project = query_db('SELECT * FROM projects WHERE project_id = ?',
                       [project_id], one=True)

    if not project or project['status'] not in ('IN_PROGRESS', 'APPROVED'):
        flash('Project not ready for final submission.', 'danger')
        return redirect(url_for('student.dashboard'))

    if not query_db('SELECT * FROM team_members WHERE team_id = ? AND student_id = ?',
                    [project['team_id'], uid], one=True):
        flash('Access denied.', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        file = request.files.get('file')
        desc = request.form.get('description', '').strip()

        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('File type not allowed. Allowed: PDF, DOC, DOCX, PPT, PPTX.', 'danger')
            return redirect(request.url)

        original_filename = secure_filename(file.filename)
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(upload_path)

        db = get_db()
        db.execute('''
            INSERT INTO submissions
                (project_id, submitted_by, original_filename, stored_filename,
                 file_path, description, submission_type, status)
            VALUES (?, ?, ?, ?, ?, ?, 'FINAL', 'SUBMITTED')
        ''', [project_id, uid, original_filename, stored_filename,
              upload_path, desc])

        db.execute(
            "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
            "VALUES (?, ?, 'final_submitted', ?)",
            [project['faculty_id'],
             f"Final submission received for project: {project['title']}",
             project_id]
        )
        db.commit()
        flash('Final submission uploaded successfully.', 'success')
        return redirect(url_for('student.project_detail', project_id=project_id))

    return render_template('student/final_submit.html', project=project)


# ── Notifications ───────────────────────────────────────────

@student_bp.route('/notifications')
@role_required('student')
def notifications():
    uid = session['user_id']
    notifs = query_db(
        'SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC',
        [uid]
    )
    return render_template('student/notifications.html', notifications=notifs)


@student_bp.route('/notification/<int:notification_id>/read', methods=['POST'])
@role_required('student')
def notification_read(notification_id):
    db = get_db()
    db.execute(
        'UPDATE notifications SET is_read = 1 WHERE notification_id = ? AND user_id = ?',
        [notification_id, session['user_id']]
    )
    db.commit()
    return redirect(url_for('student.notifications'))


@student_bp.route('/notifications/mark-all-read', methods=['POST'])
@role_required('student')
def notifications_mark_all_read():
    db = get_db()
    db.execute(
        'UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0',
        [session['user_id']]
    )
    db.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('student.notifications'))
