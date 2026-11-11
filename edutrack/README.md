# EduTrack — Student Academic Project Management System

A complete web-based system for managing student academic projects, from assignment creation and proposal submission through milestones, feedback, and final evaluation.

## Features

- **Role-based access control** — Student, Faculty, and Administrator roles with proper authorization
- **Assignment management** — Faculty creates assignments; students view and start projects
- **Team management** — Students create teams and add members
- **Proposal workflow** — Submit, review, request revision, resubmit, and approve proposals
- **Milestone tracking** — Faculty creates milestones; students submit work per milestone
- **File uploads** — Real file upload/download for project submissions (PDF, DOC, DOCX, PPT, PPTX)
- **Faculty feedback** — Faculty reviews submissions and provides written feedback
- **Evaluation & grading** — Faculty evaluates completed projects with grades and comments
- **Notifications** — Database-backed notifications for workflow events
- **Admin oversight** — Dashboard, user management, and simple reports
- **Deadline tracking** — Visual indicators for upcoming, due soon, and overdue deadlines

## Technology Stack

| Component       | Technology                    |
|-----------------|-------------------------------|
| Backend         | Python, Flask                 |
| Database        | SQLite (via Python sqlite3)   |
| Frontend        | HTML, CSS, JavaScript         |
| UI Framework    | Bootstrap 5                   |
| Authentication  | Flask sessions, Werkzeug      |
| File Storage    | Local filesystem              |

## Project Structure

```
edutrack/
├── app.py                  # Flask application factory
├── config.py               # Configuration
├── db.py                   # Database helpers
├── schema.sql              # Database schema
├── seed.py                 # Database initialization & demo data
├── requirements.txt        # Python dependencies
├── README.md
│
├── routes/
│   ├── __init__.py         # Auth decorators
│   ├── auth.py             # Login, register, logout
│   ├── student.py          # Student routes
│   ├── faculty.py          # Faculty routes
│   └── admin.py            # Admin routes
│
├── templates/
│   ├── base.html           # Base layout
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── student/            # Student templates
│   ├── faculty/            # Faculty templates
│   └── admin/              # Admin templates
│
├── static/
│   ├── css/style.css       # Custom styles
│   └── js/main.js          # Client-side JavaScript
│
├── database/
│   └── edutrack.db         # SQLite database (created by seed.py)
│
├── uploads/                # Uploaded files (created by seed.py)
│
└── tests/
    └── test_app.py         # Automated tests
```

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Steps

1. **Clone or extract the project**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database with demo data**
   ```bash
   python seed.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://localhost:5000
   ```

## Demo Credentials

| Role      | Name                  | Email                   | Password     |
|-----------|-----------------------|-------------------------|--------------|
| Faculty   | Dr. Gireesh Kumar     | faculty@edutrack.com    | Faculty@123  |
| Student   | Saksham Gupta         | saksham@edutrack.com    | Student@123  |
| Student   | Harsha Maheshwari     | harsha@edutrack.com     | Student@123  |
| Admin     | System Administrator  | admin@edutrack.com      | Admin@123    |

## Demo Data

The seed script creates:

- **Assignment**: Software Engineering Project (due 2026-12-15)
- **Team**: CodeCrafters (Saksham + Harsha)
- **Project**: Student Academic Project Management System (status: IN PROGRESS)
- **Milestones**: Project Proposal, System Design, Implementation, Testing, Final Submission
- **Submissions**: System_Design.pdf (reviewed), Project_Implementation.pdf (submitted)
- **Feedback**: Faculty feedback on System Design submission
- **Proposal Reviews**: Revision requested → Approved
- **Notifications**: Feedback and submission notifications

## Uploads Directory

Uploaded files are stored in the `uploads/` directory. This directory is created automatically by the seed script. Supported file types: PDF, DOC, DOCX, PPT, PPTX. Maximum file size: 16 MB.

## Demonstration Workflow

### As Student (saksham@edutrack.com)
1. View dashboard with project status and milestones
2. Browse available assignments
3. View team (CodeCrafters) and members
4. Open project to see status, milestones, submissions, and feedback
5. Submit milestone work or final submission

### As Faculty (faculty@edutrack.com)
1. View dashboard with pending reviews and submissions
2. Create/edit assignments
3. Review project proposals (approve or request revision)
4. Create milestones for approved projects
5. Review submissions and provide feedback
6. Evaluate and grade completed projects

### As Admin (admin@edutrack.com)
1. View system dashboard with statistics
2. Manage users (create, activate/deactivate)
3. View all assignments and projects
4. View reports (projects by status, grades)

## Running Tests

```bash
pytest tests/ -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database not found | Run `python seed.py` to initialize |
| Login fails | Verify credentials from the table above |
| File upload fails | Check that `uploads/` directory exists and has write permissions |
| Port 5000 in use | Stop other processes on port 5000 or modify `app.py` to use a different port |
| Import errors | Ensure you're running from the `edutrack/` project directory |
| Module not found | Run `pip install -r requirements.txt` |

## License

Academic project — Software Engineering course.
