import os
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app
)
from db import get_db, query_db
from routes import role_required

faculty_bp = Blueprint('faculty', __name__, template_folder='../templates')


# ── Dashboard ───────────────────────────────────────────────

@faculty_bp.route('/dashboard')
@role_required('faculty')
def dashboard():
    fid = session['user_id']

    assignments_count = query_db(
        "SELECT COUNT(*) AS c FROM assignments WHERE faculty_id = ?",
        [fid], one=True
    )['c']

    projects_count = query_db(
        "SELECT COUNT(*) AS c FROM projects WHERE faculty_id = ?",
        [fid], one=True
    )['c']

    pending_reviews_count = query_db(
        "SELECT COUNT(*) AS c FROM projects WHERE faculty_id = ? AND status = 'UNDER_REVIEW'",
        [fid], one=True
    )['c']

    pending_projects = query_db('''
        SELECT p.*, a.title AS assignment_title, t.team_name
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE p.faculty_id = ? AND p.status = 'UNDER_REVIEW'
        ORDER BY p.submitted_at DESC
    ''', [fid])

    recent_submissions = query_db('''
        SELECT s.*, m.title AS milestone_title, p.title AS project_title,
               p.project_id, u.name AS student_name
        FROM submissions s
        LEFT JOIN milestones m ON s.milestone_id = m.milestone_id
        JOIN projects p ON s.project_id = p.project_id
        JOIN users u ON s.submitted_by = u.user_id
        WHERE p.faculty_id = ?
        ORDER BY s.submitted_at DESC LIMIT 5
    ''', [fid])

    my_assignments = query_db('''
        SELECT a.*,
               (SELECT COUNT(*) FROM projects WHERE assignment_id = a.assignment_id) AS projects_count
        FROM assignments a
        WHERE a.faculty_id = ?
        ORDER BY a.created_at DESC LIMIT 5
    ''', [fid])

    return render_template(
        'faculty/dashboard.html',
        assignments_count=assignments_count,
        projects_count=projects_count,
        pending_reviews_count=pending_reviews_count,
        pending_projects=pending_projects,
        recent_submissions=recent_submissions,
        my_assignments=my_assignments
    )


# ── Assignments ─────────────────────────────────────────────

@faculty_bp.route('/assignments')
@role_required('faculty')
def assignments():
    fid = session['user_id']
    q = request.args.get('q', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT a.*,
               (SELECT COUNT(*) FROM projects WHERE assignment_id = a.assignment_id) AS projects_count
        FROM assignments a WHERE a.faculty_id = ?
    '''
    params = [fid]

    if q:
        sql += ' AND a.title LIKE ?'
        params.append(f'%{q}%')
    if status_filter:
        sql += ' AND a.status = ?'
        params.append(status_filter)

    sql += ' ORDER BY a.created_at DESC'
    assigns = query_db(sql, params)
    return render_template('faculty/assignments.html',
                           assignments=assigns, q=q, status_filter=status_filter)


@faculty_bp.route('/assignment/create', methods=['GET', 'POST'])
@role_required('faculty')
def assignment_create():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        instructions = request.form.get('instructions', '').strip()
        deadline = request.form.get('deadline', '').strip()
        status = request.form.get('status', 'OPEN')

        if not title:
            flash('Title is required.', 'danger')
            return render_template('faculty/assignment_create.html')

        if status not in ('OPEN', 'CLOSED'):
            status = 'OPEN'

        # Convert empty deadline to None
        if not deadline:
            deadline = None

        db = get_db()
        cur = db.execute('''
            INSERT INTO assignments (title, description, instructions, faculty_id, deadline, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [title, description, instructions, session['user_id'], deadline, status])
        db.commit()
        flash('Assignment created successfully.', 'success')
        return redirect(url_for('faculty.assignment_detail',
                                assignment_id=cur.lastrowid))

    return render_template('faculty/assignment_create.html')


@faculty_bp.route('/assignment/<int:assignment_id>')
@role_required('faculty')
def assignment_detail(assignment_id):
    assignment = query_db(
        'SELECT * FROM assignments WHERE assignment_id = ? AND faculty_id = ?',
        [assignment_id, session['user_id']], one=True
    )
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('faculty.assignments'))

    projects = query_db('''
        SELECT p.*, t.team_name
        FROM projects p
        JOIN teams t ON p.team_id = t.team_id
        WHERE p.assignment_id = ?
        ORDER BY p.created_at DESC
    ''', [assignment_id])

    return render_template('faculty/assignment_detail.html',
                           assignment=assignment, projects=projects)


@faculty_bp.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@role_required('faculty')
def assignment_edit(assignment_id):
    assignment = query_db(
        'SELECT * FROM assignments WHERE assignment_id = ? AND faculty_id = ?',
        [assignment_id, session['user_id']], one=True
    )
    if not assignment:
        flash('Assignment not found.', 'danger')
        return redirect(url_for('faculty.assignments'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        instructions = request.form.get('instructions', '').strip()
        deadline = request.form.get('deadline', '').strip()
        status = request.form.get('status', 'OPEN')

        if not title:
            flash('Title is required.', 'danger')
            return render_template('faculty/assignment_edit.html', assignment=assignment)

        db = get_db()
        db.execute('''
            UPDATE assignments
            SET title = ?, description = ?, instructions = ?, deadline = ?,
                status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE assignment_id = ?
        ''', [title, description, instructions, deadline, status, assignment_id])
        db.commit()
        flash('Assignment updated successfully.', 'success')
        return redirect(url_for('faculty.assignment_detail', assignment_id=assignment_id))

    return render_template('faculty/assignment_edit.html', assignment=assignment)


# ── Projects ────────────────────────────────────────────────

@faculty_bp.route('/projects')
@role_required('faculty')
def projects():
    fid = session['user_id']
    q = request.args.get('q', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT p.*, a.title AS assignment_title, t.team_name
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE p.faculty_id = ?
    '''
    params = [fid]

    if q:
        sql += ' AND p.title LIKE ?'
        params.append(f'%{q}%')
    if status_filter:
        sql += ' AND p.status = ?'
        params.append(status_filter)

    sql += ' ORDER BY p.updated_at DESC'
    projs = query_db(sql, params)
    return render_template('faculty/projects.html',
                           projects=projs, q=q, status_filter=status_filter)


@faculty_bp.route('/project/<int:project_id>')
@role_required('faculty')
def project_detail(project_id):
    project = query_db('''
        SELECT p.*, a.title AS assignment_title, t.team_name
        FROM projects p
        JOIN assignments a ON p.assignment_id = a.assignment_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE p.project_id = ? AND p.faculty_id = ?
    ''', [project_id, session['user_id']], one=True)

    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('faculty.projects'))

    team_members = query_db('''
        SELECT u.name, u.email
        FROM users u JOIN team_members tm ON u.user_id = tm.student_id
        WHERE tm.team_id = ?
    ''', [project['team_id']])

    reviews = query_db('''
        SELECT pr.*, u.name AS faculty_name
        FROM proposal_reviews pr
        JOIN users u ON pr.faculty_id = u.user_id
        WHERE pr.project_id = ?
        ORDER BY pr.created_at ASC
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
        'JOIN users u ON e.faculty_id = u.user_id '
        'WHERE e.project_id = ?',
        [project_id], one=True
    )

    return render_template(
        'faculty/project_detail.html',
        project=project, team_members=team_members, reviews=reviews,
        milestones=milestones, submissions=submissions, evaluation=evaluation
    )


# ── Proposal Review ─────────────────────────────────────────

@faculty_bp.route('/project/<int:project_id>/review', methods=['POST'])
@role_required('faculty')
def review_proposal(project_id):
    project = query_db(
        "SELECT * FROM projects WHERE project_id = ? AND faculty_id = ?",
        [project_id, session['user_id']], one=True
    )
    if not project or project['status'] != 'UNDER_REVIEW':
        flash('Invalid action.', 'danger')
        return redirect(url_for('faculty.projects'))

    decision = request.form.get('decision')
    comment = request.form.get('comment', '').strip()

    if decision not in ('APPROVED', 'REVISION_REQUESTED'):
        flash('Invalid decision.', 'danger')
        return redirect(url_for('faculty.project_detail', project_id=project_id))

    if not comment:
        flash('Comment is required.', 'danger')
        return redirect(url_for('faculty.project_detail', project_id=project_id))

    db = get_db()

    # Insert review record (never overwrite previous reviews)
    db.execute('''
        INSERT INTO proposal_reviews (project_id, faculty_id, decision, comment)
        VALUES (?, ?, ?, ?)
    ''', [project_id, session['user_id'], decision, comment])

    # Update project status
    if decision == 'APPROVED':
        db.execute(
            "UPDATE projects SET status = 'APPROVED', approved_at = CURRENT_TIMESTAMP, "
            "updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
            [project_id]
        )
        notif_msg = f"Your proposal for '{project['title']}' has been approved!"
    else:
        db.execute(
            "UPDATE projects SET status = 'REVISION_REQUESTED', "
            "updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
            [project_id]
        )
        notif_msg = f"Revision requested for your proposal: {project['title']}"

    # Notify all team members
    members = query_db(
        'SELECT student_id FROM team_members WHERE team_id = ?',
        [project['team_id']]
    )
    for m in members:
        db.execute(
            "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
            "VALUES (?, ?, 'proposal_reviewed', ?)",
            [m['student_id'], notif_msg, project_id]
        )

    db.commit()

    if decision == 'APPROVED':
        flash('Proposal approved.', 'success')
    else:
        flash('Revision requested.', 'warning')

    return redirect(url_for('faculty.project_detail', project_id=project_id))


@faculty_bp.route('/project/<int:project_id>/set-in-progress', methods=['POST'])
@role_required('faculty')
def set_in_progress(project_id):
    project = query_db(
        "SELECT * FROM projects WHERE project_id = ? AND faculty_id = ? AND status = 'APPROVED'",
        [project_id, session['user_id']], one=True
    )
    if not project:
        flash('Invalid action.', 'danger')
        return redirect(url_for('faculty.projects'))

    db = get_db()
    db.execute(
        "UPDATE projects SET status = 'IN_PROGRESS', updated_at = CURRENT_TIMESTAMP "
        "WHERE project_id = ?",
        [project_id]
    )

    members = query_db('SELECT student_id FROM team_members WHERE team_id = ?',
                       [project['team_id']])
    for m in members:
        db.execute(
            "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
            "VALUES (?, ?, 'status_update', ?)",
            [m['student_id'], f"Project '{project['title']}' is now In Progress.", project_id]
        )

    db.commit()
    flash('Project is now In Progress.', 'success')
    return redirect(url_for('faculty.project_detail', project_id=project_id))


# ── Milestones ──────────────────────────────────────────────

@faculty_bp.route('/project/<int:project_id>/milestone/create', methods=['GET', 'POST'])
@role_required('faculty')
def milestone_create(project_id):
    project = query_db(
        "SELECT * FROM projects WHERE project_id = ? AND faculty_id = ?",
        [project_id, session['user_id']], one=True
    )
    if not project or project['status'] not in ('APPROVED', 'IN_PROGRESS'):
        flash('Cannot create milestones for this project.', 'danger')
        return redirect(url_for('faculty.projects'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '').strip()

        if not title:
            flash('Title is required.', 'danger')
            return render_template('faculty/milestone_create.html', project=project)

        # Convert empty due_date to None
        if not due_date:
            due_date = None

        db = get_db()
        db.execute('''
            INSERT INTO milestones (project_id, title, description, due_date, status)
            VALUES (?, ?, ?, ?, 'PENDING')
        ''', [project_id, title, description, due_date])

        # Auto-set project to IN_PROGRESS if still APPROVED
        if project['status'] == 'APPROVED':
            db.execute(
                "UPDATE projects SET status = 'IN_PROGRESS', updated_at = CURRENT_TIMESTAMP "
                "WHERE project_id = ?",
                [project_id]
            )

        members = query_db('SELECT student_id FROM team_members WHERE team_id = ?',
                           [project['team_id']])
        for m in members:
            db.execute(
                "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
                "VALUES (?, ?, 'milestone_created', ?)",
                [m['student_id'],
                 f"New milestone '{title}' created for project: {project['title']}",
                 project_id]
            )

        db.commit()
        flash('Milestone created successfully.', 'success')
        return redirect(url_for('faculty.project_detail', project_id=project_id))

    return render_template('faculty/milestone_create.html', project=project)


@faculty_bp.route('/project/<int:project_id>/milestone/<int:milestone_id>/edit',
                  methods=['GET', 'POST'])
@role_required('faculty')
def milestone_edit(project_id, milestone_id):
    project = query_db(
        'SELECT * FROM projects WHERE project_id = ? AND faculty_id = ?',
        [project_id, session['user_id']], one=True
    )
    milestone = query_db(
        'SELECT * FROM milestones WHERE milestone_id = ? AND project_id = ?',
        [milestone_id, project_id], one=True
    )
    if not project or not milestone:
        flash('Not found.', 'danger')
        return redirect(url_for('faculty.projects'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '').strip()

        if not title:
            flash('Title is required.', 'danger')
            return render_template('faculty/milestone_edit.html',
                                   project=project, milestone=milestone)

        db = get_db()
        db.execute('''
            UPDATE milestones SET title = ?, description = ?, due_date = ?,
                   updated_at = CURRENT_TIMESTAMP
            WHERE milestone_id = ?
        ''', [title, description, due_date, milestone_id])
        db.commit()
        flash('Milestone updated.', 'success')
        return redirect(url_for('faculty.project_detail', project_id=project_id))

    return render_template('faculty/milestone_edit.html',
                           project=project, milestone=milestone)


@faculty_bp.route('/project/<int:project_id>/milestone/<int:milestone_id>/complete',
                  methods=['POST'])
@role_required('faculty')
def milestone_complete(project_id, milestone_id):
    project = query_db(
        'SELECT * FROM projects WHERE project_id = ? AND faculty_id = ?',
        [project_id, session['user_id']], one=True
    )
    milestone = query_db(
        'SELECT * FROM milestones WHERE milestone_id = ? AND project_id = ?',
        [milestone_id, project_id], one=True
    )
    if not project or not milestone:
        flash('Not found.', 'danger')
        return redirect(url_for('faculty.projects'))

    db = get_db()
    db.execute(
        "UPDATE milestones SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP "
        "WHERE milestone_id = ?",
        [milestone_id]
    )

    members = query_db('SELECT student_id FROM team_members WHERE team_id = ?',
                       [project['team_id']])
    for m in members:
        db.execute(
            "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
            "VALUES (?, ?, 'milestone_completed', ?)",
            [m['student_id'],
             f"Milestone '{milestone['title']}' marked as completed.",
             project_id]
        )

    db.commit()
    flash('Milestone marked as completed.', 'success')
    return redirect(url_for('faculty.project_detail', project_id=project_id))


# ── Submissions & Feedback ──────────────────────────────────

@faculty_bp.route('/submission/<int:submission_id>')
@role_required('faculty')
def submission_detail(submission_id):
    submission = query_db('''
        SELECT s.*, u.name AS student_name, m.title AS milestone_title,
               p.title AS project_title, p.project_id
        FROM submissions s
        JOIN users u ON s.submitted_by = u.user_id
        LEFT JOIN milestones m ON s.milestone_id = m.milestone_id
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.submission_id = ? AND p.faculty_id = ?
    ''', [submission_id, session['user_id']], one=True)

    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('faculty.projects'))

    feedbacks = query_db('''
        SELECT f.*, u.name AS faculty_name
        FROM feedback f JOIN users u ON f.faculty_id = u.user_id
        WHERE f.submission_id = ?
        ORDER BY f.created_at DESC
    ''', [submission_id])

    return render_template('faculty/submission_detail.html',
                           submission=submission, feedbacks=feedbacks)


@faculty_bp.route('/submission/<int:submission_id>/feedback', methods=['POST'])
@role_required('faculty')
def add_feedback(submission_id):
    submission = query_db('''
        SELECT s.*, p.project_id, p.title AS project_title, p.team_id
        FROM submissions s
        JOIN projects p ON s.project_id = p.project_id
        WHERE s.submission_id = ? AND p.faculty_id = ?
    ''', [submission_id, session['user_id']], one=True)

    if not submission:
        flash('Submission not found.', 'danger')
        return redirect(url_for('faculty.projects'))

    comment = request.form.get('comment', '').strip()
    if not comment:
        flash('Comment is required.', 'danger')
        return redirect(url_for('faculty.submission_detail',
                                submission_id=submission_id))

    db = get_db()
    db.execute(
        'INSERT INTO feedback (submission_id, faculty_id, comment) VALUES (?, ?, ?)',
        [submission_id, session['user_id'], comment]
    )
    db.execute(
        "UPDATE submissions SET status = 'REVIEWED' WHERE submission_id = ?",
        [submission_id]
    )

    # Notify the student who submitted
    db.execute(
        "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
        "VALUES (?, ?, 'feedback_added', ?)",
        [submission['submitted_by'],
         f"Faculty feedback added to your submission for project: {submission['project_title']}",
         submission['project_id']]
    )

    db.commit()
    flash('Feedback added successfully.', 'success')
    return redirect(url_for('faculty.submission_detail',
                            submission_id=submission_id))


# ── Evaluation ──────────────────────────────────────────────

@faculty_bp.route('/project/<int:project_id>/evaluate', methods=['GET', 'POST'])
@role_required('faculty')
def evaluate_project(project_id):
    project = query_db(
        'SELECT * FROM projects WHERE project_id = ? AND faculty_id = ?',
        [project_id, session['user_id']], one=True
    )
    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('faculty.projects'))

    existing_eval = query_db(
        'SELECT * FROM evaluations WHERE project_id = ?',
        [project_id], one=True
    )

    if request.method == 'POST':
        grade = request.form.get('grade', '').strip()
        comments = request.form.get('comments', '').strip()

        if not grade:
            flash('Grade is required.', 'danger')
            return render_template('faculty/evaluate.html',
                                   project=project, evaluation=existing_eval)

        db = get_db()
        if existing_eval:
            db.execute('''
                UPDATE evaluations SET grade = ?, comments = ?,
                       evaluated_at = CURRENT_TIMESTAMP
                WHERE evaluation_id = ?
            ''', [grade, comments, existing_eval['evaluation_id']])
        else:
            db.execute('''
                INSERT INTO evaluations (project_id, faculty_id, grade, comments)
                VALUES (?, ?, ?, ?)
            ''', [project_id, session['user_id'], grade, comments])

        db.execute(
            "UPDATE projects SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP, "
            "updated_at = CURRENT_TIMESTAMP WHERE project_id = ?",
            [project_id]
        )

        members = query_db('SELECT student_id FROM team_members WHERE team_id = ?',
                           [project['team_id']])
        for m in members:
            db.execute(
                "INSERT INTO notifications (user_id, message, notification_type, related_project_id) "
                "VALUES (?, ?, 'project_evaluated', ?)",
                [m['student_id'],
                 f"Project '{project['title']}' has been evaluated. Grade: {grade}",
                 project_id]
            )

        db.commit()
        flash('Evaluation saved. Project is now Completed.', 'success')
        return redirect(url_for('faculty.project_detail', project_id=project_id))

    return render_template('faculty/evaluate.html',
                           project=project, evaluation=existing_eval)


# ── Notifications ───────────────────────────────────────────

@faculty_bp.route('/notifications')
@role_required('faculty')
def notifications():
    notifs = query_db(
        'SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC',
        [session['user_id']]
    )
    return render_template('faculty/notifications.html', notifications=notifs)


@faculty_bp.route('/notification/<int:notification_id>/read', methods=['POST'])
@role_required('faculty')
def notification_read(notification_id):
    db = get_db()
    db.execute(
        'UPDATE notifications SET is_read = 1 WHERE notification_id = ? AND user_id = ?',
        [notification_id, session['user_id']]
    )
    db.commit()
    return redirect(url_for('faculty.notifications'))


@faculty_bp.route('/notifications/mark-all-read', methods=['POST'])
@role_required('faculty')
def notifications_mark_all_read():
    db = get_db()
    db.execute(
        'UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0',
        [session['user_id']]
    )
    db.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('faculty.notifications'))
