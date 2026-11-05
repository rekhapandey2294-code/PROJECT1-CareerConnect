import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, abort, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from database import get_db_connection

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------------------------------------------------
# HELPER FUNCTIONS & DECORATORS
# -------------------------------------------------------------

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Decorator to ensure user is logged in as a student."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in as a student.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'student':
            flash('Access restricted to students only.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to ensure user is logged in as an administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in as an administrator.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            flash('Administrator privileges required.', 'danger')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user_context():
    """Inject current user and portal stats into all Jinja templates."""
    current_user = None
    unread_count = 0
    if 'user_id' in session:
        conn = get_db_connection()
        user_row = conn.execute(
            "SELECT id, name, email, role FROM users WHERE id = ?",
            (session['user_id'],)
        ).fetchone()
        if user_row:
            current_user = dict(user_row)
        conn.close()
    return dict(current_user=current_user, current_year=datetime.now().year)

# -------------------------------------------------------------
# 1. PUBLIC ROUTES (Home, About, Auth)
# -------------------------------------------------------------

@app.route('/')
def home():
    """1. Home Page: landing page with hero, search, featured jobs and statistics."""
    conn = get_db_connection()
    
    # Placement Portal Metrics
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_placed = conn.execute("SELECT COUNT(DISTINCT user_id) FROM applications WHERE status = 'Selected'").fetchone()[0]
    total_companies = conn.execute("SELECT COUNT(DISTINCT company_name) FROM jobs").fetchone()[0]
    
    # 6 Recent active jobs for showcase
    featured_jobs = conn.execute(
        """SELECT * FROM jobs 
           WHERE is_active = 1 
           ORDER BY created_at DESC LIMIT 6"""
    ).fetchall()
    
    conn.close()
    return render_template(
        'index.html',
        total_jobs=total_jobs,
        total_students=total_students,
        total_placed=total_placed,
        total_companies=total_companies,
        featured_jobs=featured_jobs
    )

@app.route('/about')
def about():
    """2. About Us Page: placement mission, key features and cell information."""
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """3. Signup Page: student registration."""
    if 'user_id' in session:
        return redirect(url_for('student_dashboard' if session.get('role') == 'student' else 'admin_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        department = request.form.get('department', '').strip()
        roll_number = request.form.get('roll_number', '').strip()

        # Validation
        if not name or not email or not password:
            flash('All required fields must be filled.', 'danger')
            return render_template('auth/signup.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/signup.html')

        conn = get_db_connection()
        try:
            # Check existing email
            existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing_user:
                flash('An account with this email address already exists. Please login.', 'warning')
                return render_template('auth/signup.html')

            # Create user account
            pw_hash = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'student')",
                (name, email, pw_hash)
            )
            user_id = cursor.lastrowid

            # Create initial profile
            cursor.execute(
                """INSERT INTO student_profiles (user_id, department, roll_number) 
                   VALUES (?, ?, ?)""",
                (user_id, department, roll_number)
            )
            conn.commit()

            flash('Registration successful! You can now log in with your credentials.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred during registration: {e}', 'danger')
        finally:
            conn.close()

    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """4. Login Page: handles both student and admin authentication."""
    if 'user_id' in session:
        return redirect(url_for('student_dashboard' if session.get('role') == 'student' else 'admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('auth/login.html')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            # Store credentials in session
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            flash(f'Welcome back, {user["name"]}!', 'success')
            next_page = request.args.get('next')

            if user['role'] == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            else:
                return redirect(next_page or url_for('student_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """Logout current user and clear session."""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# -------------------------------------------------------------
# 2. STUDENT MODULE (Dashboard, Profile, Resume, Applications)
# -------------------------------------------------------------

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    """5. Student Dashboard: personalized stats, status overview, recommendations."""
    user_id = session['user_id']
    conn = get_db_connection()

    # Application counts for student
    stats = {
        'total_applied': conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)).fetchone()[0],
        'under_review': conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Under Review'", (user_id,)).fetchone()[0],
        'shortlisted': conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Shortlisted'", (user_id,)).fetchone()[0],
        'selected': conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Selected'", (user_id,)).fetchone()[0],
        'rejected': conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'Rejected'", (user_id,)).fetchone()[0]
    }

    # Student Profile Completion Check
    profile = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,)).fetchone()
    education_count = conn.execute("SELECT COUNT(*) FROM education WHERE user_id = ?", (user_id,)).fetchone()[0]
    skills_count = conn.execute("SELECT COUNT(*) FROM skills WHERE user_id = ?", (user_id,)).fetchone()[0]

    # Calculate completion percentage
    completion_score = 20  # Base registration
    if profile:
        if profile['phone']: completion_score += 15
        if profile['department']: completion_score += 15
        if profile['resume_filename']: completion_score += 20
        if profile['bio']: completion_score += 10
    if education_count > 0: completion_score += 10
    if skills_count > 0: completion_score += 10
    completion_percentage = min(completion_score, 100)

    # Recent Applications
    recent_applications = conn.execute(
        """SELECT a.*, j.title, j.company_name, j.location, j.job_type, j.salary_range
           FROM applications a
           JOIN jobs j ON a.job_id = j.id
           WHERE a.user_id = ?
           ORDER BY a.applied_at DESC LIMIT 5""",
        (user_id,)
    ).fetchall()

    # Recommended Jobs (Active jobs student hasn't applied to yet)
    recommended_jobs = conn.execute(
        """SELECT * FROM jobs 
           WHERE is_active = 1 
           AND id NOT IN (SELECT job_id FROM applications WHERE user_id = ?)
           ORDER BY created_at DESC LIMIT 4""",
        (user_id,)
    ).fetchall()

    conn.close()
    return render_template(
        'student/dashboard.html',
        stats=stats,
        profile=profile,
        completion_percentage=completion_percentage,
        recent_applications=recent_applications,
        recommended_jobs=recommended_jobs
    )

@app.route('/student/profile', methods=['GET', 'POST'])
@student_required
def student_profile():
    """6. Student Profile: edit personal details, education, skills & upload resume."""
    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            phone = request.form.get('phone', '').strip()
            roll_number = request.form.get('roll_number', '').strip()
            department = request.form.get('department', '').strip()
            batch_year = request.form.get('batch_year') or None
            bio = request.form.get('bio', '').strip()
            linkedin_url = request.form.get('linkedin_url', '').strip()
            github_url = request.form.get('github_url', '').strip()

            conn.execute(
                """UPDATE student_profiles 
                   SET phone = ?, roll_number = ?, department = ?, batch_year = ?, 
                       bio = ?, linkedin_url = ?, github_url = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?""",
                (phone, roll_number, department, batch_year, bio, linkedin_url, github_url, user_id)
            )
            conn.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('student_profile'))

        elif action == 'upload_resume':
            if 'resume' not in request.files:
                flash('No file selected.', 'warning')
                return redirect(url_for('student_profile'))

            file = request.files['resume']
            if file.filename == '':
                flash('No file selected.', 'warning')
                return redirect(url_for('student_profile'))

            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"resume_uid_{user_id}_{int(datetime.now().timestamp())}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
                file.save(filepath)

                conn.execute(
                    "UPDATE student_profiles SET resume_filename = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (safe_name, user_id)
                )
                conn.commit()
                flash('Resume uploaded and attached to your profile!', 'success')
                return redirect(url_for('student_profile'))
            else:
                flash('Invalid file format. Please upload PDF, DOC, or DOCX only.', 'danger')
                return redirect(url_for('student_profile'))

    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    profile = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,)).fetchone()
    education_list = conn.execute("SELECT * FROM education WHERE user_id = ? ORDER BY start_year DESC", (user_id,)).fetchall()
    skills_list = conn.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()

    return render_template(
        'student/profile.html',
        user=user,
        profile=profile,
        education_list=education_list,
        skills_list=skills_list
    )

@app.route('/student/education/add', methods=['POST'])
@student_required
def add_education():
    """Add an education entry."""
    degree = request.form.get('degree', '').strip()
    institution = request.form.get('institution', '').strip()
    start_year = request.form.get('start_year')
    end_year = request.form.get('end_year') or None
    grade_or_cgpa = request.form.get('grade_or_cgpa', '').strip()

    if not degree or not institution or not start_year:
        flash('Degree, Institution, and Start Year are required.', 'warning')
        return redirect(url_for('student_profile'))

    conn = get_db_connection()
    conn.execute(
        """INSERT INTO education (user_id, degree, institution, start_year, end_year, grade_or_cgpa) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session['user_id'], degree, institution, start_year, end_year, grade_or_cgpa)
    )
    conn.commit()
    conn.close()

    flash('Education details added successfully!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/student/education/delete/<int:edu_id>', methods=['POST'])
@student_required
def delete_education(edu_id):
    """Delete an education record."""
    conn = get_db_connection()
    conn.execute("DELETE FROM education WHERE id = ? AND user_id = ?", (edu_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Education record removed.', 'info')
    return redirect(url_for('student_profile'))

@app.route('/student/skill/add', methods=['POST'])
@student_required
def add_skill():
    """Add a new skill."""
    skill_name = request.form.get('skill_name', '').strip()
    proficiency = request.form.get('proficiency', 'Intermediate')

    if not skill_name:
        flash('Please enter a skill name.', 'warning')
        return redirect(url_for('student_profile'))

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO skills (user_id, skill_name, proficiency) VALUES (?, ?, ?)",
        (session['user_id'], skill_name, proficiency)
    )
    conn.commit()
    conn.close()

    flash(f'Skill "{skill_name}" added!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/student/skill/delete/<int:skill_id>', methods=['POST'])
@student_required
def delete_skill(skill_id):
    """Remove a skill."""
    conn = get_db_connection()
    conn.execute("DELETE FROM skills WHERE id = ? AND user_id = ?", (skill_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Skill removed.', 'info')
    return redirect(url_for('student_profile'))

@app.route('/student/applications')
@student_required
def my_applications():
    """10. My Applications Page: track all job applications and live status."""
    user_id = session['user_id']
    conn = get_db_connection()
    applications = conn.execute(
        """SELECT a.*, j.title, j.company_name, j.location, j.job_type, j.salary_range, j.deadline
           FROM applications a
           JOIN jobs j ON a.job_id = j.id
           WHERE a.user_id = ?
           ORDER BY a.applied_at DESC""",
        (user_id,)
    ).fetchall()
    conn.close()

    return render_template('student/applications.html', applications=applications)

@app.route('/resumes/<path:filename>')
@login_required
def view_resume(filename):
    """Secure resume download and preview."""
    # Prevent directory traversal
    safe_name = secure_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_name)

# -------------------------------------------------------------
# 3. JOBS MODULE (Browse, Search, Filter, Details, Apply)
# -------------------------------------------------------------

@app.route('/jobs')
def job_listings():
    """7. Job Listing Page: browse jobs with search & multi-attribute filters."""
    keyword = request.args.get('keyword', '').strip()
    job_type = request.args.get('job_type', '').strip()
    location = request.args.get('location', '').strip()
    department = request.args.get('department', '').strip()

    conn = get_db_connection()

    query = "SELECT * FROM jobs WHERE is_active = 1"
    params = []

    if keyword:
        query += " AND (title LIKE ? OR company_name LIKE ? OR description LIKE ? OR requirements LIKE ?)"
        wildcard = f"%{keyword}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if job_type:
        query += " AND job_type = ?"
        params.append(job_type)

    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    if department:
        query += " AND department LIKE ?"
        params.append(f"%{department}%")

    query += " ORDER BY created_at DESC"
    jobs = conn.execute(query, params).fetchall()

    # Distinct filter options for dropdowns
    departments = conn.execute("SELECT DISTINCT department FROM jobs WHERE department IS NOT NULL AND department != ''").fetchall()
    job_types = conn.execute("SELECT DISTINCT job_type FROM jobs").fetchall()

    # If logged in as student, get list of applied job IDs
    applied_job_ids = set()
    if 'user_id' in session and session.get('role') == 'student':
        rows = conn.execute("SELECT job_id FROM applications WHERE user_id = ?", (session['user_id'],)).fetchall()
        applied_job_ids = {r['job_id'] for r in rows}

    conn.close()

    return render_template(
        'jobs/index.html',
        jobs=jobs,
        keyword=keyword,
        job_type=job_type,
        location=location,
        department=department,
        departments=[d['department'] for d in departments],
        job_types=[jt['job_type'] for jt in job_types],
        applied_job_ids=applied_job_ids
    )

@app.route('/jobs/<int:job_id>')
def job_details(job_id):
    """8. Job Details Page: complete job overview, requirements and application CTA."""
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    if not job:
        conn.close()
        flash('Job opening not found.', 'danger')
        return redirect(url_for('job_listings'))

    has_applied = False
    application = None
    if 'user_id' in session and session.get('role') == 'student':
        application = conn.execute(
            "SELECT * FROM applications WHERE job_id = ? AND user_id = ?",
            (job_id, session['user_id'])
        ).fetchone()
        has_applied = application is not None

    similar_jobs = conn.execute(
        "SELECT * FROM jobs WHERE id != ? AND is_active = 1 AND job_type = ? LIMIT 3",
        (job_id, job['job_type'])
    ).fetchall()

    conn.close()

    return render_template(
        'jobs/detail.html',
        job=job,
        has_applied=has_applied,
        application=application,
        similar_jobs=similar_jobs
    )

@app.route('/jobs/<int:job_id>/apply', methods=['GET', 'POST'])
@student_required
def apply_job(job_id):
    """9. Apply for Job Page: application submission with resume and cover note."""
    user_id = session['user_id']
    conn = get_db_connection()

    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job or not job['is_active']:
        conn.close()
        flash('This job posting is no longer accepting applications.', 'warning')
        return redirect(url_for('job_listings'))

    # Check if already applied
    existing_app = conn.execute(
        "SELECT id FROM applications WHERE job_id = ? AND user_id = ?",
        (job_id, user_id)
    ).fetchone()
    if existing_app:
        conn.close()
        flash('You have already applied for this position.', 'info')
        return redirect(url_for('job_details', job_id=job_id))

    profile = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,)).fetchone()

    if request.method == 'POST':
        cover_note = request.form.get('cover_note', '').strip()

        # Handle resume: existing or new upload
        resume_file = request.files.get('new_resume')
        if resume_file and resume_file.filename != '':
            if allowed_file(resume_file.filename):
                ext = resume_file.filename.rsplit('.', 1)[1].lower()
                safe_name = f"resume_uid_{user_id}_{int(datetime.now().timestamp())}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
                resume_file.save(filepath)

                # Update student profile with latest resume
                conn.execute(
                    "UPDATE student_profiles SET resume_filename = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (safe_name, user_id)
                )
            else:
                conn.close()
                flash('Invalid file format. Upload PDF, DOC, or DOCX.', 'danger')
                return render_template('jobs/apply.html', job=job, profile=profile)
        elif not profile or not profile['resume_filename']:
            conn.close()
            flash('Please upload your resume before submitting your application.', 'warning')
            return render_template('jobs/apply.html', job=job, profile=profile)

        try:
            conn.execute(
                """INSERT INTO applications (job_id, user_id, status, cover_note) 
                   VALUES (?, ?, 'Pending', ?)""",
                (job_id, user_id, cover_note)
            )
            conn.commit()
            flash('Congratulations! Your application has been submitted successfully.', 'success')
            return redirect(url_for('my_applications'))
        except sqlite3.IntegrityError:
            flash('You have already applied for this job.', 'warning')
            return redirect(url_for('job_details', job_id=job_id))
        finally:
            conn.close()

    conn.close()
    return render_template('jobs/apply.html', job=job, profile=profile)

# -------------------------------------------------------------
# 4. ADMIN MODULE (Dashboard, Manage Jobs, Students, Applications)
# -------------------------------------------------------------

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """11. Admin Dashboard: overview stats, analytics, and recent applications."""
    conn = get_db_connection()

    stats = {
        'total_jobs': conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        'active_jobs': conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0],
        'total_students': conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0],
        'total_applications': conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
        'shortlisted': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Shortlisted'").fetchone()[0],
        'selected': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Selected'").fetchone()[0],
        'pending': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Pending'").fetchone()[0],
        'rejected': conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Rejected'").fetchone()[0]
    }

    # Recent applications with student and job details
    recent_applications = conn.execute(
        """SELECT a.*, u.name as student_name, u.email as student_email, 
                  j.title as job_title, j.company_name, sp.roll_number, sp.department
           FROM applications a
           JOIN users u ON a.user_id = u.id
           JOIN jobs j ON a.job_id = j.id
           LEFT JOIN student_profiles sp ON u.id = sp.user_id
           ORDER BY a.applied_at DESC LIMIT 6"""
    ).fetchall()

    # Top hiring companies
    company_stats = conn.execute(
        """SELECT company_name, COUNT(*) as opening_count 
           FROM jobs 
           GROUP BY company_name 
           ORDER BY opening_count DESC LIMIT 5"""
    ).fetchall()

    conn.close()
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_applications=recent_applications,
        company_stats=company_stats
    )

@app.route('/admin/jobs')
@admin_required
def manage_jobs():
    """12. Manage Jobs Page: view, search, toggle status, edit or delete jobs."""
    conn = get_db_connection()
    jobs = conn.execute(
        """SELECT j.*, COUNT(a.id) as applicant_count 
           FROM jobs j 
           LEFT JOIN applications a ON j.id = a.job_id 
           GROUP BY j.id 
           ORDER BY j.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template('admin/manage_jobs.html', jobs=jobs)

@app.route('/admin/jobs/new', methods=['GET', 'POST'])
@admin_required
def create_job():
    """Add a new job opening."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company_name = request.form.get('company_name', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', 'Full-time')
        salary_range = request.form.get('salary_range', '').strip()
        department = request.form.get('department', '').strip()
        vacancies = int(request.form.get('vacancies', 1))
        deadline = request.form.get('deadline') or None
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        company_logo = request.form.get('company_logo', 'bi-briefcase')

        if not title or not company_name or not location or not description:
            flash('Please fill in all mandatory job fields.', 'warning')
            return render_template('admin/job_form.html', job=None, action='Create')

        conn = get_db_connection()
        conn.execute(
            """INSERT INTO jobs 
               (title, company_name, company_logo, location, job_type, salary_range, 
                department, description, requirements, vacancies, deadline, is_active, created_by) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (title, company_name, company_logo, location, job_type, salary_range,
             department, description, requirements, vacancies, deadline, session['user_id'])
        )
        conn.commit()
        conn.close()

        flash(f'Job "{title}" at {company_name} posted successfully!', 'success')
        return redirect(url_for('manage_jobs'))

    return render_template('admin/job_form.html', job=None, action='Create')

@app.route('/admin/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_job(job_id):
    """Edit existing job opening."""
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    if not job:
        conn.close()
        flash('Job not found.', 'danger')
        return redirect(url_for('manage_jobs'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company_name = request.form.get('company_name', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', 'Full-time')
        salary_range = request.form.get('salary_range', '').strip()
        department = request.form.get('department', '').strip()
        vacancies = int(request.form.get('vacancies', 1))
        deadline = request.form.get('deadline') or None
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        company_logo = request.form.get('company_logo', 'bi-briefcase')
        is_active = 1 if request.form.get('is_active') == '1' else 0

        conn.execute(
            """UPDATE jobs 
               SET title = ?, company_name = ?, company_logo = ?, location = ?, 
                   job_type = ?, salary_range = ?, department = ?, description = ?, 
                   requirements = ?, vacancies = ?, deadline = ?, is_active = ?
               WHERE id = ?""",
            (title, company_name, company_logo, location, job_type, salary_range,
             department, description, requirements, vacancies, deadline, is_active, job_id)
        )
        conn.commit()
        conn.close()

        flash('Job details updated successfully.', 'success')
        return redirect(url_for('manage_jobs'))

    conn.close()
    return render_template('admin/job_form.html', job=job, action='Edit')

@app.route('/admin/jobs/<int:job_id>/delete', methods=['POST'])
@admin_required
def delete_job(job_id):
    """Delete a job posting."""
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    flash('Job posting deleted successfully.', 'info')
    return redirect(url_for('manage_jobs'))

@app.route('/admin/jobs/<int:job_id>/toggle', methods=['POST'])
@admin_required
def toggle_job_status(job_id):
    """Toggle job between Active and Inactive."""
    conn = get_db_connection()
    job = conn.execute("SELECT is_active FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job:
        new_status = 0 if job['is_active'] == 1 else 1
        conn.execute("UPDATE jobs SET is_active = ? WHERE id = ?", (new_status, job_id))
        conn.commit()
        flash('Job status updated.', 'info')
    conn.close()
    return redirect(url_for('manage_jobs'))

@app.route('/admin/students')
@admin_required
def manage_students():
    """13. Manage Students Page: list registered students, search, and view profiles."""
    keyword = request.args.get('keyword', '').strip()
    department = request.args.get('department', '').strip()

    conn = get_db_connection()
    query = """
        SELECT u.id, u.name, u.email, u.created_at,
               sp.roll_number, sp.department, sp.batch_year, sp.phone, sp.resume_filename,
               COUNT(DISTINCT a.id) as applications_count,
               COUNT(DISTINCT s.id) as skills_count
        FROM users u
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        LEFT JOIN applications a ON u.id = a.user_id
        LEFT JOIN skills s ON u.id = s.user_id
        WHERE u.role = 'student'
    """
    params = []

    if keyword:
        query += " AND (u.name LIKE ? OR u.email LIKE ? OR sp.roll_number LIKE ?)"
        wildcard = f"%{keyword}%"
        params.extend([wildcard, wildcard, wildcard])

    if department:
        query += " AND sp.department LIKE ?"
        params.append(f"%{department}%")

    query += " GROUP BY u.id ORDER BY u.created_at DESC"

    students = conn.execute(query, params).fetchall()
    departments = conn.execute("SELECT DISTINCT department FROM student_profiles WHERE department IS NOT NULL AND department != ''").fetchall()
    conn.close()

    return render_template(
        'admin/manage_students.html',
        students=students,
        keyword=keyword,
        department=department,
        departments=[d['department'] for d in departments]
    )

@app.route('/admin/students/<int:student_id>')
@admin_required
def view_student_detail(student_id):
    """Comprehensive Admin view of student details, resumes and past applications."""
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM users WHERE id = ? AND role = 'student'", (student_id,)).fetchone()

    if not student:
        conn.close()
        flash('Student record not found.', 'danger')
        return redirect(url_for('manage_students'))

    profile = conn.execute("SELECT * FROM student_profiles WHERE user_id = ?", (student_id,)).fetchone()
    education = conn.execute("SELECT * FROM education WHERE user_id = ? ORDER BY start_year DESC", (student_id,)).fetchall()
    skills = conn.execute("SELECT * FROM skills WHERE user_id = ?", (student_id,)).fetchall()
    applications = conn.execute(
        """SELECT a.*, j.title, j.company_name, j.location, j.job_type 
           FROM applications a 
           JOIN jobs j ON a.job_id = j.id 
           WHERE a.user_id = ? 
           ORDER BY a.applied_at DESC""",
        (student_id,)
    ).fetchall()

    conn.close()
    return render_template(
        'admin/student_detail.html',
        student=student,
        profile=profile,
        education=education,
        skills=skills,
        applications=applications
    )

@app.route('/admin/applications')
@admin_required
def manage_applications():
    """14. Manage Applications Page: filter, shortlist, reject, and update statuses."""
    status_filter = request.args.get('status', '').strip()
    job_filter = request.args.get('job_id', '').strip()
    keyword = request.args.get('keyword', '').strip()

    conn = get_db_connection()

    query = """
        SELECT a.*, u.id as student_id, u.name as student_name, u.email as student_email,
               sp.roll_number, sp.department, sp.phone, sp.resume_filename,
               j.title as job_title, j.company_name, j.location, j.job_type
        FROM applications a
        JOIN users u ON a.user_id = u.id
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN student_profiles sp ON u.id = sp.user_id
        WHERE 1 = 1
    """
    params = []

    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)

    if job_filter:
        query += " AND a.job_id = ?"
        params.append(job_filter)

    if keyword:
        query += " AND (u.name LIKE ? OR u.email LIKE ? OR j.title LIKE ? OR j.company_name LIKE ?)"
        wildcard = f"%{keyword}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    query += " ORDER BY a.applied_at DESC"
    applications = conn.execute(query, params).fetchall()

    jobs_list = conn.execute("SELECT id, title, company_name FROM jobs ORDER BY title ASC").fetchall()
    conn.close()

    return render_template(
        'admin/manage_applications.html',
        applications=applications,
        status_filter=status_filter,
        job_filter=job_filter,
        keyword=keyword,
        jobs_list=jobs_list
    )

@app.route('/admin/applications/<int:app_id>/status', methods=['POST'])
@admin_required
def update_application_status(app_id):
    """Update status of a student's job application (Pending, Under Review, Shortlisted, Rejected, Selected)."""
    new_status = request.form.get('status')
    valid_statuses = ['Pending', 'Under Review', 'Shortlisted', 'Rejected', 'Selected']

    if new_status not in valid_statuses:
        flash('Invalid status selected.', 'danger')
        return redirect(request.referrer or url_for('manage_applications'))

    conn = get_db_connection()
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, app_id)
    )
    conn.commit()
    conn.close()

    flash(f'Application status updated to "{new_status}".', 'success')
    return redirect(request.referrer or url_for('manage_applications'))

# -------------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', not_found=True), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html', server_error=True), 500

if __name__ == '__main__':
    # Initialize DB on first run if needed
    init_db()
    seed_db()
    print("\n" + "="*60)
    print("🚀 CareerConnect Placement Portal is running at: http://127.0.0.1:5000")
    print("👤 Admin Login:    admin@careerconnect.com / admin123")
    print("🎓 Student Login:  rahul@careerconnect.com / student123")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)
