import requests

# Test login page
r = requests.get('http://127.0.0.1:5000/login')
print('Login page:', r.status_code)

# Test login
s = requests.Session()
r = s.post('http://127.0.0.1:5000/login', data={'email': 'saksham@edutrack.com', 'password': 'Student@123'}, allow_redirects=False)
print('Login POST:', r.status_code, r.headers.get('Location', ''))

r = s.get('http://127.0.0.1:5000/student/dashboard')
print('Student dashboard:', r.status_code, 'len=', len(r.text))

r = s.get('http://127.0.0.1:5000/student/assignments')
print('Student assignments:', r.status_code)

r = s.get('http://127.0.0.1:5000/student/project/1')
print('Student project:', r.status_code)

r = s.get('http://127.0.0.1:5000/student/teams')
print('Student teams:', r.status_code)

r = s.get('http://127.0.0.1:5000/student/notifications')
print('Student notifications:', r.status_code)

# Logout and test faculty
s.get('http://127.0.0.1:5000/logout')
r = s.post('http://127.0.0.1:5000/login', data={'email': 'faculty@edutrack.com', 'password': 'Faculty@123'}, allow_redirects=False)
print('Faculty login:', r.status_code, r.headers.get('Location', ''))

r = s.get('http://127.0.0.1:5000/faculty/dashboard')
print('Faculty dashboard:', r.status_code)

r = s.get('http://127.0.0.1:5000/faculty/assignments')
print('Faculty assignments:', r.status_code)

r = s.get('http://127.0.0.1:5000/faculty/project/1')
print('Faculty project:', r.status_code)

r = s.get('http://127.0.0.1:5000/faculty/projects')
print('Faculty projects:', r.status_code)

# Logout and test admin
s.get('http://127.0.0.1:5000/logout')
r = s.post('http://127.0.0.1:5000/login', data={'email': 'admin@edutrack.com', 'password': 'Admin@123'}, allow_redirects=False)
print('Admin login:', r.status_code, r.headers.get('Location', ''))

r = s.get('http://127.0.0.1:5000/admin/dashboard')
print('Admin dashboard:', r.status_code)

r = s.get('http://127.0.0.1:5000/admin/users')
print('Admin users:', r.status_code)

r = s.get('http://127.0.0.1:5000/admin/projects')
print('Admin projects:', r.status_code)

r = s.get('http://127.0.0.1:5000/admin/reports')
print('Admin reports:', r.status_code)

# Test authorization
s2 = requests.Session()
s2.post('http://127.0.0.1:5000/login', data={'email': 'saksham@edutrack.com', 'password': 'Student@123'})
r = s2.get('http://127.0.0.1:5000/faculty/dashboard')
print('Student->faculty (expect 403):', r.status_code)
r = s2.get('http://127.0.0.1:5000/admin/dashboard')
print('Student->admin (expect 403):', r.status_code)
