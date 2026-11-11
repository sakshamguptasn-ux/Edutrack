"""
EduTrack — Database Seed Script
Creates the database, tables, and inserts demo data.
"""
import os
import sys
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add project root to path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from config import Config


def seed():
    """Initialize database and insert demo data."""
    # Ensure database directory exists
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Remove existing database for clean seed
    if os.path.exists(Config.DATABASE):
        os.remove(Config.DATABASE)
        print("[INFO] Removed existing database.")

    # Connect and create tables
    conn = sqlite3.connect(Config.DATABASE)
    conn.execute('PRAGMA foreign_keys = ON')
    cursor = conn.cursor()

    # Read and execute schema
    schema_path = os.path.join(BASE_DIR, 'schema.sql')
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    print("[OK] Database tables created.")

    # ── Demo Users ──────────────────────────────────────────
    users = [
        ('Dr. Gireesh Kumar', 'faculty@edutrack.com',
         generate_password_hash('Faculty@123'), 'faculty', 1),
        ('Saksham Gupta', 'saksham@edutrack.com',
         generate_password_hash('Student@123'), 'student', 1),
        ('Harsha Maheshwari', 'harsha@edutrack.com',
         generate_password_hash('Student@123'), 'student', 1),
        ('System Administrator', 'admin@edutrack.com',
         generate_password_hash('Admin@123'), 'admin', 1),
    ]
    cursor.executemany(
        'INSERT INTO users (name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)',
        users
    )
    conn.commit()
    print("[OK] Demo users created.")

    # Get user IDs
    faculty_id = cursor.execute("SELECT user_id FROM users WHERE email='faculty@edutrack.com'").fetchone()[0]
    saksham_id = cursor.execute("SELECT user_id FROM users WHERE email='saksham@edutrack.com'").fetchone()[0]
    harsha_id = cursor.execute("SELECT user_id FROM users WHERE email='harsha@edutrack.com'").fetchone()[0]

    # ── Demo Assignment ─────────────────────────────────────
    cursor.execute('''
        INSERT INTO assignments (title, description, instructions, faculty_id, deadline, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        'Software Engineering Project',
        'Develop a software system following the Software Engineering lifecycle.',
        'Form a team, submit a project proposal, complete the assigned milestones, submit the required project documents, and complete the final project evaluation.',
        faculty_id,
        '2026-12-15',
        'OPEN'
    ))
    conn.commit()
    assignment_id = cursor.lastrowid
    print("[OK] Demo assignment created.")

    # ── Demo Team ───────────────────────────────────────────
    cursor.execute('''
        INSERT INTO teams (team_name, created_by) VALUES (?, ?)
    ''', ('CodeCrafters', saksham_id))
    conn.commit()
    team_id = cursor.lastrowid

    # Add team members
    cursor.execute('INSERT INTO team_members (team_id, student_id) VALUES (?, ?)', (team_id, saksham_id))
    cursor.execute('INSERT INTO team_members (team_id, student_id) VALUES (?, ?)', (team_id, harsha_id))
    conn.commit()
    print("[OK] Demo team 'CodeCrafters' created with members.")

    # ── Demo Project ────────────────────────────────────────
    cursor.execute('''
        INSERT INTO projects (assignment_id, team_id, faculty_id, title, description, status,
                              submitted_at, approved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        assignment_id,
        team_id,
        faculty_id,
        'Student Academic Project Management System',
        'A centralized system for managing student academic projects from assignment and proposal submission through milestones, feedback and final evaluation.',
        'IN_PROGRESS',
        '2026-09-20 10:00:00',
        '2026-09-25 14:30:00'
    ))
    conn.commit()
    project_id = cursor.lastrowid
    print("[OK] Demo project created.")

    # ── Demo Proposal Reviews ───────────────────────────────
    cursor.execute('''
        INSERT INTO proposal_reviews (project_id, faculty_id, decision, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        project_id, faculty_id, 'REVISION_REQUESTED',
        'Please clarify the project objectives and describe the proposed system modules.',
        '2026-09-22 11:00:00'
    ))
    cursor.execute('''
        INSERT INTO proposal_reviews (project_id, faculty_id, decision, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        project_id, faculty_id, 'APPROVED',
        'Revised proposal reviewed and approved.',
        '2026-09-25 14:30:00'
    ))
    conn.commit()
    print("[OK] Demo proposal review history created.")

    # ── Demo Milestones ─────────────────────────────────────
    milestones = [
        ('Project Proposal', 'Submit the initial project proposal document.', '2026-10-10', 'COMPLETED'),
        ('System Design', 'Create system architecture, UML diagrams, and design documentation.', '2026-10-25', 'COMPLETED'),
        ('Implementation', 'Implement the core system modules and features.', '2026-11-15', 'SUBMITTED'),
        ('Testing', 'Perform unit testing, integration testing, and user acceptance testing.', '2026-11-30', 'PENDING'),
        ('Final Submission', 'Submit the final project with documentation and presentation.', '2026-12-10', 'PENDING'),
    ]
    milestone_ids = {}
    for title, desc, due, status in milestones:
        cursor.execute('''
            INSERT INTO milestones (project_id, title, description, due_date, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (project_id, title, desc, due, status))
        milestone_ids[title] = cursor.lastrowid
    conn.commit()
    print("[OK] Demo milestones created.")

    # ── Demo Placeholder Files ──────────────────────────────
    # Create placeholder PDF files for demo submissions
    demo_files = {
        'System_Design.pdf': 'system_design_demo.pdf',
        'Project_Implementation.pdf': 'project_implementation_demo.pdf',
    }
    for original, stored in demo_files.items():
        filepath = os.path.join(Config.UPLOAD_FOLDER, stored)
        with open(filepath, 'w') as f:
            f.write(f'%PDF-1.4\n% Demo placeholder for {original}\n'
                    f'% This is a demo file created by the EduTrack seed script.\n')
    print("[OK] Demo placeholder files created.")

    # ── Demo Submissions ────────────────────────────────────
    cursor.execute('''
        INSERT INTO submissions (project_id, milestone_id, submitted_by, original_filename,
                                 stored_filename, file_path, description, submission_type, status, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id,
        milestone_ids['System Design'],
        saksham_id,
        'System_Design.pdf',
        'system_design_demo.pdf',
        os.path.join(Config.UPLOAD_FOLDER, 'system_design_demo.pdf'),
        'System design document including architecture diagrams and module descriptions.',
        'MILESTONE',
        'REVIEWED',
        '2026-10-24 09:00:00'
    ))
    submission1_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO submissions (project_id, milestone_id, submitted_by, original_filename,
                                 stored_filename, file_path, description, submission_type, status, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id,
        milestone_ids['Implementation'],
        saksham_id,
        'Project_Implementation.pdf',
        'project_implementation_demo.pdf',
        os.path.join(Config.UPLOAD_FOLDER, 'project_implementation_demo.pdf'),
        'Implementation document covering core modules and code structure.',
        'MILESTONE',
        'SUBMITTED',
        '2026-11-14 16:00:00'
    ))
    conn.commit()
    print("[OK] Demo submissions created.")

    # ── Demo Feedback ───────────────────────────────────────
    cursor.execute('''
        INSERT INTO feedback (submission_id, faculty_id, comment, created_at)
        VALUES (?, ?, ?, ?)
    ''', (
        submission1_id,
        faculty_id,
        'System design and documentation are satisfactory. Continue with implementation and ensure that all required workflows are tested.',
        '2026-10-26 10:00:00'
    ))
    conn.commit()
    print("[OK] Demo feedback created.")

    # ── Demo Notifications ──────────────────────────────────
    notifications = [
        (saksham_id, 'Faculty feedback has been added to your System Design submission.',
         'feedback', project_id, assignment_id, 0),
        (saksham_id, 'Your Implementation milestone is awaiting faculty review.',
         'submission', project_id, assignment_id, 0),
        (harsha_id, 'Faculty feedback has been added to your System Design submission.',
         'feedback', project_id, assignment_id, 0),
        (harsha_id, 'Your Implementation milestone is awaiting faculty review.',
         'submission', project_id, assignment_id, 0),
        (faculty_id, 'A new Implementation submission has been received from the CodeCrafters team.',
         'submission', project_id, assignment_id, 0),
    ]
    cursor.executemany('''
        INSERT INTO notifications (user_id, message, notification_type, related_project_id,
                                   related_assignment_id, is_read)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', notifications)
    conn.commit()
    print("[OK] Demo notifications created.")

    conn.close()
    print("\n" + "=" * 50)
    print("  EduTrack database seeded successfully!")
    print("=" * 50)
    print("\nDemo Accounts:")
    print("  Faculty:  faculty@edutrack.com  / Faculty@123")
    print("  Student:  saksham@edutrack.com  / Student@123")
    print("  Student:  harsha@edutrack.com   / Student@123")
    print("  Admin:    admin@edutrack.com    / Admin@123")
    print(f"\nDatabase: {Config.DATABASE}")
    print(f"Uploads:  {Config.UPLOAD_FOLDER}")
    print("\nRun the app with: python app.py")


if __name__ == '__main__':
    seed()
