import os
import logging
from flask import render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, Student, Teacher, Course, Attendance, StudentCourse
from forms import LoginForm, RegisterForm, CourseForm, ProfilePhotoForm
from recognition import process_capture_image, extract_face_encoding, recognize_faces
from datetime import datetime
import base64
import json

logger = logging.getLogger(__name__)

def register_routes(app):
    # Home route
    @app.route('/')
    def index():
        return redirect(url_for('login'))

    # Authentication routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            if current_user.role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
                
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                
                if user.role == 'student':
                    return redirect(next_page or url_for('student_dashboard'))
                else:
                    return redirect(next_page or url_for('teacher_dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        
        return render_template('login.html', form=form, title='Login')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        form = RegisterForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            if form.role.data == 'student':
                student = Student(
                    user_id=user.id,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data
                )
                db.session.add(student)
            else:
                teacher = Teacher(
                    user_id=user.id,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data
                )
                db.session.add(teacher)
                
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        return render_template('register.html', form=form, title='Register')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # Student routes
    @app.route('/student/dashboard')
    @login_required
    def student_dashboard():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('index'))
            
        student = Student.query.filter_by(user_id=current_user.id).first()
        
        # Get student courses
        student_courses = StudentCourse.query.filter_by(student_id=student.id).all()
        courses = [sc.course for sc in student_courses]
        
        # Calculate attendance stats
        attendance_stats = []
        for course in courses:
            total_sessions = Attendance.query.filter_by(
                student_id=student.id, 
                course_id=course.id
            ).count()
            
            present_sessions = Attendance.query.filter_by(
                student_id=student.id, 
                course_id=course.id,
                status=True
            ).count()
            
            attendance_percentage = 0 if total_sessions == 0 else (present_sessions / total_sessions) * 100
            
            attendance_stats.append({
                'course': course.name,
                'total_sessions': total_sessions,
                'present_sessions': present_sessions,
                'attendance_percentage': round(attendance_percentage, 2)
            })
        
        return render_template(
            'student/dashboard.html', 
            student=student,
            courses=courses,
            attendance_stats=attendance_stats,
            title='Student Dashboard'
        )

    @app.route('/student/profile', methods=['GET', 'POST'])
    @login_required
    def student_profile():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('index'))
            
        student = Student.query.filter_by(user_id=current_user.id).first()
        form = ProfilePhotoForm()
        
        if form.validate_on_submit():
            flash('Please capture your profile photo below', 'info')
            
        return render_template(
            'student/profile.html', 
            student=student, 
            form=form,
            title='Student Profile'
        )

    @app.route('/student/save_face', methods=['POST'])
    @login_required
    def save_face():
        if current_user.role != 'student':
            return jsonify({'success': False, 'message': 'Access denied'})
            
        student = Student.query.filter_by(user_id=current_user.id).first()
        
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'})
            
        try:
            image_data = request.json.get('image')
            
            if not image_data:
                return jsonify({'success': False, 'message': 'No image data provided'})
                
            # For demo purposes, we're not actually processing the image
            # but we'll simulate the process
            
            # Create a simulated face encoding
            face_encoding, face_count = extract_face_encoding("dummy_image")
            
            # Save the face encoding and profile image
            student.face_encoding = face_encoding
            student.profile_image = image_data
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Face saved successfully'})
        except Exception as e:
            logger.error(f"Error saving face: {e}")
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
            
    @app.route('/student/browse_courses')
    @login_required
    def browse_courses():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('index'))
            
        student = Student.query.filter_by(user_id=current_user.id).first()
        
        # Get all courses
        all_courses = Course.query.all()
        
        # Get courses this student is already enrolled in
        enrolled_course_ids = set(enrollment.course_id for enrollment in 
                              StudentCourse.query.filter_by(student_id=student.id).all())
        
        # Prepare course data with enrollment status
        available_courses = []
        for course in all_courses:
            teacher = Teacher.query.get(course.teacher_id)
            teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown"
            
            available_courses.append({
                'id': course.id,
                'name': course.name,
                'description': course.description,
                'teacher_name': teacher_name,
                'enrolled': course.id in enrolled_course_ids
            })
        
        return render_template(
            'student/enroll_courses.html',
            student=student,
            available_courses=available_courses,
            title='Browse Courses'
        )
        
    @app.route('/student/enroll', methods=['POST'])
    @login_required
    def enroll_in_course():
        if current_user.role != 'student':
            return jsonify({'success': False, 'message': 'Access denied'})
            
        student = Student.query.filter_by(user_id=current_user.id).first()
        
        # Get course ID from request
        data = request.json
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'success': False, 'message': 'No course specified'})
            
        # Check if course exists
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'success': False, 'message': 'Course not found'})
            
        # Check if already enrolled
        existing_enrollment = StudentCourse.query.filter_by(
            student_id=student.id,
            course_id=course.id
        ).first()
        
        if existing_enrollment:
            return jsonify({'success': False, 'message': 'You are already enrolled in this course'})
            
        # Create enrollment record
        enrollment = StudentCourse(
            student_id=student.id,
            course_id=course.id
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully enrolled in {course.name}!'
        })

    # Teacher routes
    @app.route('/teacher/dashboard')
    @login_required
    def teacher_dashboard():
        if current_user.role != 'teacher':
            flash('Access denied. Teachers only.', 'danger')
            return redirect(url_for('index'))
            
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        courses = Course.query.filter_by(teacher_id=teacher.id).all()
        
        # Calculate overall statistics
        course_stats = []
        for course in courses:
            student_count = StudentCourse.query.filter_by(course_id=course.id).count()
            
            # Get today's attendance
            today = datetime.now().date()
            today_attendances = Attendance.query.filter_by(
                course_id=course.id,
                date=today
            ).all()
            
            present_today = sum(1 for a in today_attendances if a.status)
            
            # Calculate percentage for today
            today_percentage = 0 if student_count == 0 else (present_today / student_count) * 100
            
            course_stats.append({
                'course': course.name,
                'student_count': student_count,
                'present_today': present_today,
                'today_percentage': round(today_percentage, 2)
            })
        
        return render_template(
            'teacher/dashboard.html', 
            teacher=teacher,
            courses=courses,
            course_stats=course_stats,
            title='Teacher Dashboard'
        )

    @app.route('/teacher/courses', methods=['GET', 'POST'])
    @login_required
    def manage_courses():
        if current_user.role != 'teacher':
            flash('Access denied. Teachers only.', 'danger')
            return redirect(url_for('index'))
            
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        form = CourseForm()
        
        if form.validate_on_submit():
            course = Course(
                name=form.name.data,
                description=form.description.data,
                teacher_id=teacher.id
            )
            db.session.add(course)
            db.session.commit()
            flash('Course created successfully!', 'success')
            return redirect(url_for('manage_courses'))
            
        courses = Course.query.filter_by(teacher_id=teacher.id).all()
        
        return render_template(
            'teacher/courses.html', 
            teacher=teacher,
            courses=courses,
            form=form,
            title='Manage Courses'
        )

    @app.route('/teacher/capture/<int:course_id>', methods=['GET'])
    @login_required
    def capture_attendance(course_id):
        if current_user.role != 'teacher':
            flash('Access denied. Teachers only.', 'danger')
            return redirect(url_for('index'))
            
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
        
        if not course:
            flash('Course not found or unauthorized', 'danger')
            return redirect(url_for('teacher_dashboard'))
            
        # Get enrolled students for this course
        student_courses = StudentCourse.query.filter_by(course_id=course.id).all()
        students = [sc.student for sc in student_courses]
        
        return render_template(
            'teacher/capture.html', 
            teacher=teacher,
            course=course,
            students=students,
            title=f'Capture Attendance - {course.name}'
        )

    @app.route('/teacher/process_attendance', methods=['POST'])
    @login_required
    def process_attendance():
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'message': 'Access denied'})
            
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        
        try:
            # Get data from the request
            data = request.json
            image_data = data.get('image')
            course_id = data.get('course_id')
            
            course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
            
            if not course:
                return jsonify({'success': False, 'message': 'Course not found or unauthorized'})
                
            # Get enrolled students for this course
            student_courses = StudentCourse.query.filter_by(course_id=course.id).all()
            enrolled_students = [sc.student for sc in student_courses]
            
            # Get face encodings for all enrolled students
            known_face_encodings = []
            known_student_ids = []
            
            for student in enrolled_students:
                if student.face_encoding is not None:
                    known_face_encodings.append(student.face_encoding)
                    known_student_ids.append(student.id)
            
            # For demo purposes, we're skipping the actual image processing step
            # Call the recognize_faces function with the dummy image data
            recognized_student_ids = recognize_faces("dummy_image", known_face_encodings, known_student_ids)
            
            # Mark attendance for recognized students
            today = datetime.now().date()
            
            # Create attendance records for all students (default to absent)
            for student in enrolled_students:
                # Check if attendance record already exists
                attendance = Attendance.query.filter_by(
                    student_id=student.id,
                    course_id=course.id,
                    date=today
                ).first()
                
                if not attendance:
                    attendance = Attendance(
                        student_id=student.id,
                        course_id=course.id,
                        date=today,
                        status=False
                    )
                    db.session.add(attendance)
            
            # Update status for recognized students
            for student_id in recognized_student_ids:
                attendance = Attendance.query.filter_by(
                    student_id=student_id,
                    course_id=course.id,
                    date=today
                ).first()
                
                if attendance:
                    attendance.status = True
            
            db.session.commit()
            
            # Get recognized student names
            recognized_students = []
            for student_id in recognized_student_ids:
                student = Student.query.get(student_id)
                if student:
                    recognized_students.append(f"{student.first_name} {student.last_name}")
            
            # Return success response with recognized students
            return jsonify({
                'success': True, 
                'message': f'Attendance recorded for {len(recognized_student_ids)} students',
                'recognized_students': recognized_students
            })
            
        except Exception as e:
            logger.error(f"Error processing attendance: {e}")
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})

    @app.route('/teacher/attendance_list/<int:course_id>')
    @login_required
    def attendance_list(course_id):
        if current_user.role != 'teacher':
            flash('Access denied. Teachers only.', 'danger')
            return redirect(url_for('index'))
            
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
        
        if not course:
            flash('Course not found or unauthorized', 'danger')
            return redirect(url_for('teacher_dashboard'))
            
        # Get all dates with attendance records for this course
        dates = db.session.query(Attendance.date).filter_by(course_id=course.id).distinct().all()
        dates = [date[0] for date in dates]
        dates.sort(reverse=True)  # Most recent first
        
        # Get enrolled students
        student_courses = StudentCourse.query.filter_by(course_id=course.id).all()
        students = [sc.student for sc in student_courses]
        
        # Build attendance data
        attendance_data = {}
        for student in students:
            attendance_data[student.id] = {
                'name': f"{student.first_name} {student.last_name}",
                'records': {}
            }
            
            # Get all attendance records for this student
            attendances = Attendance.query.filter_by(
                student_id=student.id,
                course_id=course.id
            ).all()
            
            for attendance in attendances:
                attendance_data[student.id]['records'][attendance.date.isoformat()] = attendance.status
        
        return render_template(
            'teacher/attendance_list.html', 
            teacher=teacher,
            course=course,
            dates=dates,
            attendance_data=attendance_data,
            students=students,
            title=f'Attendance List - {course.name}'
        )

    # API routes
    @app.route('/api/enroll_student', methods=['POST'])
    @login_required
    def enroll_student():
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'message': 'Access denied'})
            
        data = request.json
        course_id = data.get('course_id')
        student_email = data.get('student_email')
        
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
        
        if not course:
            return jsonify({'success': False, 'message': 'Course not found or unauthorized'})
            
        # Find student by email
        user = User.query.filter_by(email=student_email, role='student').first()
        
        if not user:
            return jsonify({'success': False, 'message': 'Student not found'})
            
        student = Student.query.filter_by(user_id=user.id).first()
        
        # Check if already enrolled
        existing_enrollment = StudentCourse.query.filter_by(
            student_id=student.id,
            course_id=course.id
        ).first()
        
        if existing_enrollment:
            return jsonify({'success': False, 'message': 'Student already enrolled in this course'})
            
        # Create enrollment
        enrollment = StudentCourse(
            student_id=student.id,
            course_id=course.id
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Enrolled {user.username} in {course.name}',
            'student': {
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}"
            }
        })
