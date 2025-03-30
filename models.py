from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'teacher'
    
    # Relationships
    student_info = db.relationship('Student', uselist=False, back_populates='user', cascade="all, delete-orphan")
    teacher_info = db.relationship('Teacher', uselist=False, back_populates='user', cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    face_encoding = db.Column(db.PickleType, nullable=True)  # Store face encoding data
    profile_image = db.Column(db.Text, nullable=True)  # Store base64 encoded image
    
    # Relationships
    user = db.relationship('User', back_populates='student_info')
    attendances = db.relationship('Attendance', back_populates='student', cascade="all, delete-orphan")
    courses = db.relationship('StudentCourse', back_populates='student', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='teacher_info')
    courses = db.relationship('Course', back_populates='teacher', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Teacher {self.first_name} {self.last_name}>'


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    
    # Relationships
    teacher = db.relationship('Teacher', back_populates='courses')
    students = db.relationship('StudentCourse', back_populates='course', cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', back_populates='course', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Course {self.name}>'


class StudentCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    
    # Relationships
    student = db.relationship('Student', back_populates='courses')
    course = db.relationship('Course', back_populates='students')
    
    def __repr__(self):
        return f'<StudentCourse {self.student_id}-{self.course_id}>'


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    status = db.Column(db.Boolean, default=False)  # True for present, False for absent
    
    # Relationships
    student = db.relationship('Student', back_populates='attendances')
    course = db.relationship('Course', back_populates='attendances')
    
    def __repr__(self):
        status_str = "Present" if self.status else "Absent"
        return f'<Attendance {self.student_id} - {self.date} - {status_str}>'
