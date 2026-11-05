import os
import sqlite3
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    """Create a database connection with dictionary-like row access."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables from schema.sql."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_db_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print("✓ Database tables initialized successfully.")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        raise e
    finally:
        conn.close()

def seed_db():
    """Seed sample data for testing and demonstrations."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if already seeded
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            print("ℹ Database already contains user records. Skipping seed.")
            return

        # 1. Insert Admin User
        admin_pass = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Placement Administrator", "admin@careerconnect.com", admin_pass, "admin")
        )
        admin_id = cursor.lastrowid

        # 2. Insert Student 1: Rahul Sharma
        student1_pass = generate_password_hash("student123")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Rahul Sharma", "rahul@careerconnect.com", student1_pass, "student")
        )
        student1_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO student_profiles 
               (user_id, phone, roll_number, department, batch_year, bio, linkedin_url, github_url) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                student1_id,
                "+91 98765 43210",
                "CS2022-042",
                "Computer Science & Engineering",
                2026,
                "Passionate computer science student passionate about backend systems, Python, and scalable web applications.",
                "https://linkedin.com/in/rahulsharma-demo",
                "https://github.com/rahulsharma-demo"
            )
        )

        # Education for Rahul
        cursor.execute(
            """INSERT INTO education (user_id, degree, institution, start_year, end_year, grade_or_cgpa) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (student1_id, "B.Tech Computer Science & Engineering", "National Institute of Technology", 2022, 2026, "8.9 CGPA")
        )
        cursor.execute(
            """INSERT INTO education (user_id, degree, institution, start_year, end_year, grade_or_cgpa) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (student1_id, "Higher Secondary (Class XII)", "Delhi Public School", 2020, 2022, "94.2%")
        )

        # Skills for Rahul
        skills_rahul = [
            ("Python", "Advanced"),
            ("Flask", "Advanced"),
            ("SQLite & PostgreSQL", "Intermediate"),
            ("HTML5 & Bootstrap 5", "Advanced"),
            ("Git & GitHub", "Intermediate"),
            ("REST APIs", "Intermediate")
        ]
        for skill_name, prof in skills_rahul:
            cursor.execute(
                "INSERT INTO skills (user_id, skill_name, proficiency) VALUES (?, ?, ?)",
                (student1_id, skill_name, prof)
            )

        # 3. Insert Student 2: Priya Patel
        student2_pass = generate_password_hash("student123")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Priya Patel", "priya@careerconnect.com", student2_pass, "student")
        )
        student2_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO student_profiles 
               (user_id, phone, roll_number, department, batch_year, bio, linkedin_url, github_url) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                student2_id,
                "+91 98111 22334",
                "IT2022-019",
                "Information Technology",
                2026,
                "Data enthusiast and front-end developer eager to build intuitive data-driven products.",
                "https://linkedin.com/in/priyapatel-demo",
                "https://github.com/priyapatel-demo"
            )
        )

        cursor.execute(
            """INSERT INTO education (user_id, degree, institution, start_year, end_year, grade_or_cgpa) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (student2_id, "B.Tech Information Technology", "State Technical University", 2022, 2026, "9.2 CGPA")
        )

        skills_priya = [
            ("Data Analysis", "Advanced"),
            ("JavaScript", "Intermediate"),
            ("Python Pandas", "Advanced"),
            ("Tableau", "Intermediate")
        ]
        for skill_name, prof in skills_priya:
            cursor.execute(
                "INSERT INTO skills (user_id, skill_name, proficiency) VALUES (?, ?, ?)",
                (student2_id, skill_name, prof)
            )

        # 4. Insert Student 3: Amit Verma
        student3_pass = generate_password_hash("student123")
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Amit Verma", "amit@careerconnect.com", student3_pass, "student")
        )
        student3_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO student_profiles 
               (user_id, phone, roll_number, department, batch_year, bio) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                student3_id,
                "+91 98222 33445",
                "EC2022-055",
                "Electronics & Communication",
                2026,
                "Hardware enthusiast bridging IoT and embedded software engineering."
            )
        )

        # 5. Insert Sample Jobs
        sample_jobs = [
            (
                "Software Development Engineer (SDE-1)",
                "TechCorp Global",
                "bi-cpu",
                "Bengaluru, India (Hybrid)",
                "Full-time",
                "₹12,00,000 - ₹15,00,000 LPA",
                "Computer Science",
                "We are seeking an enthusiastic SDE-1 to design and develop core software microservices and web modules. You will collaborate with cross-functional teams to build resilient architectures.",
                "Strong grasp of Data Structures and Algorithms; Proficiency in Python, Java, or C++; Knowledge of relational databases and RESTful API standards; Excellent problem-solving skills.",
                4,
                "2026-12-31",
                1,
                admin_id
            ),
            (
                "Python Backend Developer Intern",
                "CloudScale Systems",
                "bi-server",
                "Hyderabad, India (Remote)",
                "Internship",
                "₹30,000 / month Stipend",
                "Information Technology",
                "Join our high-velocity engineering squad to build and maintain high-throughput backend services using Python and Flask/FastAPI.",
                "Hands-on experience with Python and relational databases (SQLite/PostgreSQL); Familiarity with Git version control; Willingness to learn cloud platforms (AWS/GCP).",
                2,
                "2026-11-30",
                1,
                admin_id
            ),
            (
                "Junior Data Analyst",
                "FinTech Analytics Hub",
                "bi-graph-up-arrow",
                "Mumbai, India (On-site)",
                "Full-time",
                "₹8,00,000 - ₹10,50,000 LPA",
                "Data Science / Mathematics",
                "Empower risk and financial decision-makers by turning vast transaction logs into actionable, predictive business metrics and live dashboards.",
                "Proficiency in SQL and Python (Pandas, NumPy); Familiarity with visualization tools like Tableau or PowerBI; Strong communication skills.",
                3,
                "2026-12-15",
                1,
                admin_id
            ),
            (
                "Associate Frontend Engineer",
                "CreativeUI Labs",
                "bi-code-slash",
                "Pune, India (Hybrid)",
                "Full-time",
                "₹7,50,000 - ₹9,00,000 LPA",
                "All Engineering Streams",
                "Craft elegant, accessible, responsive web interfaces using semantic HTML5, modern CSS3, and JavaScript.",
                "Solid foundation in HTML5, CSS3, Bootstrap 5, and JavaScript; Understanding of responsive layout design; Eye for clean UI/UX.",
                2,
                "2026-12-20",
                1,
                admin_id
            ),
            (
                "Cloud & DevOps Intern",
                "Apex Cloud Networks",
                "bi-cloud-check",
                "Bengaluru, India (On-site)",
                "Internship",
                "₹25,000 / month Stipend",
                "Computer Science / IT",
                "Work directly with DevOps architects to automate CI/CD delivery pipelines, monitor cloud telemetry, and streamline container orchestration.",
                "Basics of Linux administration and shell scripting; Understanding of Docker containers and Git workflow; Passion for automation.",
                1,
                "2026-11-25",
                1,
                admin_id
            )
        ]

        job_ids = []
        for job in sample_jobs:
            cursor.execute(
                """INSERT INTO jobs 
                   (title, company_name, company_logo, location, job_type, salary_range, department, description, requirements, vacancies, deadline, is_active, created_by) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                job
            )
            job_ids.append(cursor.lastrowid)

        # 6. Insert Sample Applications
        cursor.execute(
            """INSERT INTO applications (job_id, user_id, status, cover_note) 
               VALUES (?, ?, ?, ?)""",
            (
                job_ids[0],
                student1_id,
                "Shortlisted",
                "I have solved over 300 DSA problems and built multiple full-stack Flask applications. I look forward to contributing to TechCorp!"
            )
        )
        cursor.execute(
            """INSERT INTO applications (job_id, user_id, status, cover_note) 
               VALUES (?, ?, ?, ?)""",
            (
                job_ids[1],
                student1_id,
                "Under Review",
                "Python and Flask are my primary areas of expertise. I have developed REST APIs and worked extensively with database query optimization."
            )
        )
        cursor.execute(
            """INSERT INTO applications (job_id, user_id, status, cover_note) 
               VALUES (?, ?, ?, ?)""",
            (
                job_ids[2],
                student2_id,
                "Selected",
                "I have created predictive risk pipelines using Python Pandas and SQL during my academic capstone project."
            )
        )
        cursor.execute(
            """INSERT INTO applications (job_id, user_id, status, cover_note) 
               VALUES (?, ?, ?, ?)""",
            (
                job_ids[3],
                student3_id,
                "Pending",
                "Excited to apply my frontend design and responsive styling skills to build intuitive interfaces for CreativeUI Labs."
            )
        )

        conn.commit()
        print("✓ Database seeded successfully with demo users, jobs, and applications.")
    except Exception as e:
        conn.rollback()
        print(f"✗ Error seeding database: {e}")
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if action in ('init', 'all'):
        init_db()
    if action in ('seed', 'all'):
        seed_db()
