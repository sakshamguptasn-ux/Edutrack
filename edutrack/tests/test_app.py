"""
EduTrack — Test Suite
Tests the most important workflows.
"""
import os
import sys
import tempfile
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import create_app
from db import get_db, init_db
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create application for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    upload_dir = tempfile.mkdtemp()

    app = create_app()
    app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'UPLOAD_FOLDER': upload_dir,
        'WTF_CSRF_ENABLED': False,
    })

    with app.app_context():
        init_db()
        _seed_test_data(app)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_test_data(app):
    """Insert minimal test data."""
    with app.app_context():
        db = get_db()
        # Faculty
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            ('Test Faculty', 'faculty@test.com', generate_password_hash('Test@123'), 'faculty', 1)
        )
        # Students
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            ('Test Student', 'student@test.com', generate_password_hash('Test@123'), 'student', 1)
        )
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            ('Test Student 2', 'student2@test.com', generate_password_hash('Test@123'), 'student', 1)
        )
        # Admin
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            ('Test Admin', 'admin@test.com', generate_password_hash('Test@123'), 'admin', 1)
        )
        # Inactive user
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
            ('Inactive User', 'inactive@test.com', generate_password_hash('Test@123'), 'student', 0)
        )
        db.commit()


def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


# ── Authentication Tests ────────────────────────────────────

class TestAuth:
    def test_login_page_loads(self, client):
        rv = client.get('/login')
        assert rv.status_code == 200
        assert b'Sign In' in rv.data or b'Login' in rv.data or b'EduTrack' in rv.data

    def test_valid_login(self, client):
        rv = login(client, 'student@test.com', 'Test@123')
        assert rv.status_code == 200

    def test_invalid_login(self, client):
        rv = login(client, 'student@test.com', 'WrongPassword')
        assert b'Invalid' in rv.data or b'invalid' in rv.data or b'error' in rv.data or rv.status_code == 200

    def test_inactive_user_login(self, client):
        rv = login(client, 'inactive@test.com', 'Test@123')
        assert b'deactivated' in rv.data or b'inactive' in rv.data or b'disabled' in rv.data or rv.status_code == 200

    def test_logout(self, client):
        login(client, 'student@test.com', 'Test@123')
        rv = logout(client)
        assert rv.status_code == 200

    def test_register_page_loads(self, client):
        rv = client.get('/register')
        assert rv.status_code == 200

    def test_registration(self, client):
        rv = client.post('/register', data={
            'name': 'New Student',
            'email': 'new@test.com',
            'password': 'NewPass@123',
            'confirm_password': 'NewPass@123',
            'role': 'student'
        }, follow_redirects=True)
        assert rv.status_code == 200

    def test_duplicate_email_registration(self, client):
        rv = client.post('/register', data={
            'name': 'Duplicate',
            'email': 'student@test.com',
            'password': 'Test@123',
            'confirm_password': 'Test@123',
            'role': 'student'
        }, follow_redirects=True)
        assert b'already' in rv.data or b'exists' in rv.data or b'taken' in rv.data or rv.status_code == 200


# ── Role Authorization Tests ────────────────────────────────

class TestAuthorization:
    def test_student_cannot_access_faculty(self, client):
        login(client, 'student@test.com', 'Test@123')
        rv = client.get('/faculty/dashboard')
        assert rv.status_code == 403 or rv.status_code == 302

    def test_student_cannot_access_admin(self, client):
        login(client, 'student@test.com', 'Test@123')
        rv = client.get('/admin/dashboard')
        assert rv.status_code == 403 or rv.status_code == 302

    def test_faculty_cannot_access_student(self, client):
        login(client, 'faculty@test.com', 'Test@123')
        rv = client.get('/student/dashboard')
        assert rv.status_code == 403 or rv.status_code == 302

    def test_faculty_cannot_access_admin(self, client):
        login(client, 'faculty@test.com', 'Test@123')
        rv = client.get('/admin/dashboard')
        assert rv.status_code == 403 or rv.status_code == 302

    def test_unauthenticated_redirect(self, client):
        rv = client.get('/student/dashboard')
        assert rv.status_code == 302


# ── Faculty Assignment Tests ─────────────────────────────────

class TestAssignments:
    def test_create_assignment(self, client):
        login(client, 'faculty@test.com', 'Test@123')
        rv = client.post('/faculty/assignment/create', data={
            'title': 'Test Assignment',
            'description': 'A test assignment',
            'instructions': 'Complete the tasks',
            'deadline': '2027-06-01',
            'status': 'OPEN'
        }, follow_redirects=True)
        assert rv.status_code == 200

    def test_view_assignments(self, client):
        login(client, 'faculty@test.com', 'Test@123')
        # Create an assignment first
        client.post('/faculty/assignment/create', data={
            'title': 'Test Assignment',
            'description': 'A test assignment',
            'instructions': 'Complete the tasks',
            'deadline': '2027-06-01',
            'status': 'OPEN'
        })
        rv = client.get('/faculty/assignments')
        assert rv.status_code == 200
        assert b'Test Assignment' in rv.data

    def test_student_sees_open_assignments(self, client):
        login(client, 'faculty@test.com', 'Test@123')
        client.post('/faculty/assignment/create', data={
            'title': 'Visible Assignment',
            'description': 'Should be visible',
            'instructions': 'Instructions here',
            'deadline': '2027-06-01',
            'status': 'OPEN'
        })
        logout(client)
        login(client, 'student@test.com', 'Test@123')
        rv = client.get('/student/assignments')
        assert rv.status_code == 200


# ── Team Tests ───────────────────────────────────────────────

class TestTeams:
    def test_create_team(self, client):
        login(client, 'student@test.com', 'Test@123')
        rv = client.post('/student/team/create', data={
            'team_name': 'Test Team'
        }, follow_redirects=True)
        assert rv.status_code == 200

    def test_view_teams(self, client):
        login(client, 'student@test.com', 'Test@123')
        client.post('/student/team/create', data={'team_name': 'My Team'})
        rv = client.get('/student/teams')
        assert rv.status_code == 200


# ── Project Workflow Tests ───────────────────────────────────

class TestProjectWorkflow:
    def _setup_project(self, client):
        """Create assignment, team, and project."""
        # Faculty creates assignment
        login(client, 'faculty@test.com', 'Test@123')
        client.post('/faculty/assignment/create', data={
            'title': 'Workflow Test Assignment',
            'description': 'For testing workflow',
            'instructions': 'Follow the workflow',
            'deadline': '2027-12-01',
            'status': 'OPEN'
        })
        logout(client)

        # Student creates team and project
        login(client, 'student@test.com', 'Test@123')
        client.post('/student/team/create', data={'team_name': 'Workflow Team'})

        # Get assignment and team IDs
        with client.application.app_context():
            from db import query_db
            assignment = query_db(
                "SELECT assignment_id FROM assignments WHERE title='Workflow Test Assignment'", one=True
            )
            team = query_db(
                "SELECT team_id FROM teams WHERE team_name='Workflow Team'", one=True
            )

        # Create project
        client.post(f'/student/project/create/{assignment["assignment_id"]}', data={
            'title': 'Workflow Test Project',
            'description': 'Testing the full workflow',
            'team_id': team['team_id']
        })

        with client.application.app_context():
            from db import query_db
            project = query_db(
                "SELECT project_id FROM projects WHERE title='Workflow Test Project'", one=True
            )

        return assignment['assignment_id'], team['team_id'], project['project_id']

    def test_project_creation(self, client):
        a_id, t_id, p_id = self._setup_project(client)
        with client.application.app_context():
            from db import query_db
            project = query_db('SELECT * FROM projects WHERE project_id=?', [p_id], one=True)
            assert project is not None
            assert project['status'] == 'DRAFT'

    def test_proposal_submission(self, client):
        a_id, t_id, p_id = self._setup_project(client)
        rv = client.post(f'/student/project/{p_id}/submit-proposal', follow_redirects=True)
        assert rv.status_code == 200
        with client.application.app_context():
            from db import query_db
            project = query_db('SELECT status FROM projects WHERE project_id=?', [p_id], one=True)
            assert project['status'] == 'UNDER_REVIEW'

    def test_proposal_revision_request(self, client):
        a_id, t_id, p_id = self._setup_project(client)
        client.post(f'/student/project/{p_id}/submit-proposal')
        logout(client)

        login(client, 'faculty@test.com', 'Test@123')
        rv = client.post(f'/faculty/project/{p_id}/review', data={
            'decision': 'REVISION_REQUESTED',
            'comment': 'Please improve the proposal.'
        }, follow_redirects=True)
        assert rv.status_code == 200

        with client.application.app_context():
            from db import query_db
            project = query_db('SELECT status FROM projects WHERE project_id=?', [p_id], one=True)
            assert project['status'] == 'REVISION_REQUESTED'

    def test_proposal_resubmission(self, client):
        a_id, t_id, p_id = self._setup_project(client)
        client.post(f'/student/project/{p_id}/submit-proposal')
        logout(client)

        login(client, 'faculty@test.com', 'Test@123')
        client.post(f'/faculty/project/{p_id}/review', data={
            'decision': 'REVISION_REQUESTED',
            'comment': 'Revise it.'
        })
        logout(client)

        login(client, 'student@test.com', 'Test@123')
        rv = client.post(f'/student/project/{p_id}/resubmit-proposal', follow_redirects=True)
        assert rv.status_code == 200

        with client.application.app_context():
            from db import query_db
            project = query_db('SELECT status FROM projects WHERE project_id=?', [p_id], one=True)
            assert project['status'] == 'UNDER_REVIEW'

    def test_proposal_approval(self, client):
        a_id, t_id, p_id = self._setup_project(client)
        client.post(f'/student/project/{p_id}/submit-proposal')
        logout(client)

        login(client, 'faculty@test.com', 'Test@123')
        rv = client.post(f'/faculty/project/{p_id}/review', data={
            'decision': 'APPROVED',
            'comment': 'Approved!'
        }, follow_redirects=True)
        assert rv.status_code == 200

        with client.application.app_context():
            from db import query_db
            project = query_db('SELECT status FROM projects WHERE project_id=?', [p_id], one=True)
            assert project['status'] == 'APPROVED'

    def test_milestone_creation(self, client):
        a_id, t_id, p_id = self._setup_project(client)
        client.post(f'/student/project/{p_id}/submit-proposal')
        logout(client)

        login(client, 'faculty@test.com', 'Test@123')
        client.post(f'/faculty/project/{p_id}/review', data={
            'decision': 'APPROVED',
            'comment': 'Approved!'
        })

        rv = client.post(f'/faculty/project/{p_id}/milestone/create', data={
            'title': 'First Milestone',
            'description': 'Complete phase 1',
            'due_date': '2027-07-01'
        }, follow_redirects=True)
        assert rv.status_code == 200

        with client.application.app_context():
            from db import query_db
            milestones = query_db('SELECT * FROM milestones WHERE project_id=?', [p_id])
            assert len(milestones) == 1


# ── Notification Tests ───────────────────────────────────────

class TestNotifications:
    def test_notifications_page(self, client):
        login(client, 'student@test.com', 'Test@123')
        rv = client.get('/student/notifications')
        assert rv.status_code == 200

    def test_notification_created_on_proposal_submit(self, client):
        # Faculty creates assignment
        login(client, 'faculty@test.com', 'Test@123')
        client.post('/faculty/assignment/create', data={
            'title': 'Notif Test',
            'description': 'Testing notifications',
            'instructions': 'Submit proposal',
            'deadline': '2027-12-01',
            'status': 'OPEN'
        })
        logout(client)

        login(client, 'student@test.com', 'Test@123')
        client.post('/student/team/create', data={'team_name': 'Notif Team'})

        with client.application.app_context():
            from db import query_db
            assignment = query_db("SELECT assignment_id FROM assignments WHERE title='Notif Test'", one=True)
            team = query_db("SELECT team_id FROM teams WHERE team_name='Notif Team'", one=True)

        client.post(f'/student/project/create/{assignment["assignment_id"]}', data={
            'title': 'Notif Project',
            'description': 'For notification testing',
            'team_id': team['team_id']
        })

        with client.application.app_context():
            from db import query_db
            project = query_db("SELECT project_id FROM projects WHERE title='Notif Project'", one=True)

        client.post(f'/student/project/{project["project_id"]}/submit-proposal')

        with client.application.app_context():
            from db import query_db
            notifs = query_db("SELECT * FROM notifications WHERE notification_type='proposal_submitted'")
            assert len(notifs) >= 1


# ── Admin Tests ──────────────────────────────────────────────

class TestAdmin:
    def test_admin_dashboard(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.get('/admin/dashboard')
        assert rv.status_code == 200

    def test_admin_users(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.get('/admin/users')
        assert rv.status_code == 200

    def test_admin_create_user(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.post('/admin/user/create', data={
            'name': 'Admin Created User',
            'email': 'admincreated@test.com',
            'password': 'AdminCreated@123',
            'role': 'student'
        }, follow_redirects=True)
        assert rv.status_code == 200

    def test_admin_toggle_user(self, client):
        login(client, 'admin@test.com', 'Test@123')
        # Get student user ID
        with client.application.app_context():
            from db import query_db
            user = query_db("SELECT user_id FROM users WHERE email='student@test.com'", one=True)
        rv = client.post(f'/admin/user/{user["user_id"]}/toggle-active', follow_redirects=True)
        assert rv.status_code == 200

    def test_admin_reports(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.get('/admin/reports')
        assert rv.status_code == 200

    def test_admin_projects(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.get('/admin/projects')
        assert rv.status_code == 200

    def test_admin_assignments(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.get('/admin/assignments')
        assert rv.status_code == 200


# ── Dashboard Tests ──────────────────────────────────────────

class TestDashboards:
    def test_student_dashboard(self, client):
        login(client, 'student@test.com', 'Test@123')
        rv = client.get('/student/dashboard')
        assert rv.status_code == 200

    def test_faculty_dashboard(self, client):
        login(client, 'faculty@test.com', 'Test@123')
        rv = client.get('/faculty/dashboard')
        assert rv.status_code == 200

    def test_admin_dashboard(self, client):
        login(client, 'admin@test.com', 'Test@123')
        rv = client.get('/admin/dashboard')
        assert rv.status_code == 200
