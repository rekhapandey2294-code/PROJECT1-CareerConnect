-- CareerConnect Database Schema (SQLite)
-- Enable Foreign Key constraints
PRAGMA foreign_keys = ON;

-- 1. Users Table (Stores authentication & role info)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student', 'admin')) DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Student Profiles Table (Stores detailed candidate profile)
CREATE TABLE IF NOT EXISTS student_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    phone TEXT,
    roll_number TEXT,
    department TEXT,
    batch_year INTEGER,
    bio TEXT,
    resume_filename TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Education Table (Stores academic background)
CREATE TABLE IF NOT EXISTS education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    degree TEXT NOT NULL,
    institution TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER,
    grade_or_cgpa TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Skills Table (Stores technical & soft skills)
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    proficiency TEXT CHECK(proficiency IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')) DEFAULT 'Intermediate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. Jobs Table (Stores posted placement openings)
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    company_logo TEXT,
    location TEXT NOT NULL,
    job_type TEXT NOT NULL CHECK(job_type IN ('Full-time', 'Part-time', 'Internship', 'Remote', 'Contract')) DEFAULT 'Full-time',
    salary_range TEXT,
    department TEXT,
    description TEXT NOT NULL,
    requirements TEXT NOT NULL,
    vacancies INTEGER DEFAULT 1,
    deadline DATE,
    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- 6. Applications Table (Tracks job applications and their statuses)
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('Pending', 'Under Review', 'Shortlisted', 'Rejected', 'Selected')) DEFAULT 'Pending',
    cover_note TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, user_id),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for lightning-fast queries
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_education_user ON education(user_id);
CREATE INDEX IF NOT EXISTS idx_skills_user ON skills(user_id);
