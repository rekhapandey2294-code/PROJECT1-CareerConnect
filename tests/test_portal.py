import os
import gc
import unittest
import tempfile
import sqlite3
from app import app
from database import init_db, seed_db
from config import Config

class CareerConnectTestCase(unittest.TestCase):
    """Automated test suite for CareerConnect Student Placement Portal."""

    def setUp(self):
        # Configure app for isolated testing
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)  # Close OS fd immediately so Windows file locks don't conflict
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.temp_db_path
        app.config['WTF_CSRF_ENABLED'] = False
        Config.DATABASE_PATH = self.temp_db_path
        self.client = app.test_client()

        # Initialize schema and seed test data
        init_db()
        seed_db()

    def tearDown(self):
        gc.collect()
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    # -------------------------------------------------------------
    # 1. PUBLIC ROUTES TESTS
    # -------------------------------------------------------------
    def test_home_page(self):
        """Test home page loads with HTTP 200 and displays brand."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CareerConnect', response.data)
        self.assertIn(b'Active Drives', response.data)

    def test_about_page(self):
        """Test about page renders successfully."""
        response = self.client.get('/about')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Our Mission', response.data)

    def test_job_listings_and_filters(self):
        """Test job listings page and search filtering."""
        # Unfiltered list
        res = self.client.get('/jobs')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Browse and filter verified campus job listings', res.data)

        # Keyword filter search
        res_search = self.client.get('/jobs?keyword=Python')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'Python', res_search.data)

    # -------------------------------------------------------------
    # 2. AUTHENTICATION & ACCESS CONTROL TESTS
    # -------------------------------------------------------------
    def test_student_registration_and_login(self):
        """Test new student signup and subsequent login."""
        # Register new student
        signup_data = {
            'name': 'Test New Student',
            'email': 'newstudent@careerconnect.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'department': 'Computer Science & Engineering',
            'roll_number': 'CS-TEST-99'
        }
        res_signup = self.client.post('/register', data=signup_data, follow_redirects=True)
        self.assertEqual(res_signup.status_code, 200)
        self.assertIn(b'Registration successful', res_signup.data)

        # Login with newly created student
        login_data = {
            'email': 'newstudent@careerconnect.com',
            'password': 'password123'
        }
        res_login = self.client.post('/login', data=login_data, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Welcome back', res_login.data)
        self.assertIn(b'Student Portal', res_login.data)

    def test_login_invalid_credentials(self):
        """Test login fails with incorrect password."""
        res = self.client.post('/login', data={'email': 'rahul@careerconnect.com', 'password': 'wrongpassword'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password', res.data)

    def test_admin_access_protection(self):
        """Test student cannot access admin console."""
        # Login as student
        self.client.post('/login', data={'email': 'rahul@careerconnect.com', 'password': 'student123'})
        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Administrator privileges required', res.data)

    # -------------------------------------------------------------
    # 3. STUDENT PROFILE & APPLICATION TESTS
    # -------------------------------------------------------------
    def test_student_profile_update(self):
        """Test student can update profile information."""
        self.client.post('/login', data={'email': 'rahul@careerconnect.com', 'password': 'student123'})
        update_data = {
            'action': 'update_profile',
            'phone': '+91 99999 88888',
            'roll_number': 'CS2022-042',
            'department': 'Computer Science & Engineering',
            'batch_year': '2026',
            'bio': 'Updated bio for automated tests.',
            'linkedin_url': 'https://linkedin.com/in/updated',
            'github_url': 'https://github.com/updated'
        }
        res = self.client.post('/student/profile', data=update_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Profile updated successfully', res.data)

    def test_add_and_delete_skill(self):
        """Test adding and removing a technical skill."""
        self.client.post('/login', data={'email': 'rahul@careerconnect.com', 'password': 'student123'})
        # Add skill
        res_add = self.client.post('/student/skill/add', data={'skill_name': 'Docker Containers', 'proficiency': 'Intermediate'}, follow_redirects=True)
        self.assertIn(b'Docker Containers', res_add.data)
        self.assertIn(b'added', res_add.data)

    def test_job_application_flow(self):
        """Test student applying for an available job."""
        # Login as student 3 who has fewer applications
        self.client.post('/login', data={'email': 'amit@careerconnect.com', 'password': 'student123'})
        
        # Apply for Job ID 1
        apply_data = {
            'cover_note': 'I am applying through automated unit tests!'
        }
        # First ensure profile has resume or we mock resume attached in DB
        conn = sqlite3.connect(self.temp_db_path)
        conn.execute("UPDATE student_profiles SET resume_filename = 'test_resume.pdf' WHERE user_id = 4")
        conn.commit()
        conn.close()

        res_apply = self.client.post('/jobs/1/apply', data=apply_data, follow_redirects=True)
        self.assertEqual(res_apply.status_code, 200)
        self.assertIn(b'Your application has been submitted successfully', res_apply.data)

        # Duplicate application check
        res_dup = self.client.post('/jobs/1/apply', data=apply_data, follow_redirects=True)
        self.assertIn(b'already applied', res_dup.data)

    # -------------------------------------------------------------
    # 4. ADMIN MANAGEMENT & WORKFLOW TESTS
    # -------------------------------------------------------------
    def test_admin_create_and_manage_job(self):
        """Test admin can create and delete a job posting."""
        self.client.post('/login', data={'email': 'admin@careerconnect.com', 'password': 'admin123'})
        job_data = {
            'title': 'AI Research Intern',
            'company_name': 'DeepMind Demo Labs',
            'location': 'Bengaluru, India',
            'job_type': 'Internship',
            'salary_range': '₹40,000 / month',
            'department': 'Computer Science',
            'vacancies': 2,
            'deadline': '2026-12-30',
            'description': 'Conduct exploratory experiments in reinforcement learning.',
            'requirements': 'Strong math and Python foundation.',
            'company_logo': 'bi-cpu'
        }
        res_create = self.client.post('/admin/jobs/new', data=job_data, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn(b'posted successfully', res_create.data)
        self.assertIn(b'AI Research Intern', res_create.data)

    def test_admin_update_application_status(self):
        """Test admin updating candidate application status to Shortlisted."""
        self.client.post('/login', data={'email': 'admin@careerconnect.com', 'password': 'admin123'})
        res_status = self.client.post(
            '/admin/applications/1/status',
            data={'status': 'Shortlisted'},
            follow_redirects=True
        )
        self.assertEqual(res_status.status_code, 200)
        self.assertIn(b'Application status updated', res_status.data)

if __name__ == '__main__':
    unittest.main()
