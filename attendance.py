import os
import base64
import io
import logging
import numpy as np
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, Course, StudentCourse, AttendanceSession, Attendance
from face_recognition_utils import detect_faces_from_image, compare_faces
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

attendance = Blueprint('attendance', __name__)

class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired()])
    code = StringField('Course Code', validators=[DataRequired()])
    submit = SubmitField('Create Course')

@attendance.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_teacher:
            return redirect(url_for('attendance.teacher_dashboard'))
        else:
            return redirect(url_for('attendance.student_dashboard'))
    return redirect(url_for('auth.login'))

@attendance.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher:
        flash('Access denied: You are not a teacher', 'danger')
        return redirect(url_for('attendance.student_dashboard'))
    
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    
    # Get some basic statistics for display
    course_stats = []
    for course in courses:
        sessions = AttendanceSession.query.filter_by(course_id=course.id).all()
        total_sessions = len(sessions)
        
        # Get number of enrolled students
        enrolled_count = StudentCourse.query.filter_by(course_id=course.id).count()
        
        # Calculate average attendance percentage
        avg_attendance = 0
        if total_sessions > 0:
            present_count = 0
            total_possible = 0
            for session in sessions:
                session_present = Attendance.query.filter_by(session_id=session.id, is_present=True).count()
                session_total = Attendance.query.filter_by(session_id=session.id).count()
                present_count += session_present
                total_possible += session_total
            
            if total_possible > 0:
                avg_attendance = round((present_count / total_possible) * 100, 2)
        
        course_stats.append({
            'course': course,
            'enrolled_students': enrolled_count,
            'total_sessions': total_sessions,
            'avg_attendance': avg_attendance
        })
    
    return render_template('teacher_dashboard.html', 
                          title='Teacher Dashboard', 
                          course_stats=course_stats)

@attendance.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_teacher:
        flash('Access denied: You are a teacher', 'danger')
        return redirect(url_for('attendance.teacher_dashboard'))
    
    # Get courses the student is enrolled in
    enrolled_courses = StudentCourse.query.filter_by(student_id=current_user.id).all()
    
    course_attendance = []
    for enrollment in enrolled_courses:
        course = Course.query.get(enrollment.course_id)
        sessions = AttendanceSession.query.filter_by(course_id=course.id).all()
        
        # Calculate attendance for this course
        total_sessions = len(sessions)
        sessions_attended = 0
        
        for session in sessions:
            attendance_record = Attendance.query.filter_by(
                student_id=current_user.id,
                session_id=session.id,
                is_present=True
            ).first()
            
            if attendance_record:
                sessions_attended += 1
        
        attendance_percentage = 0
        if total_sessions > 0:
            attendance_percentage = (sessions_attended / total_sessions) * 100
        
        course_attendance.append({
            'course': course,
            'sessions_attended': sessions_attended,
            'total_sessions': total_sessions,
            'attendance_percentage': round(attendance_percentage, 2)
        })
    
    return render_template('student_dashboard.html', 
                          title='Student Dashboard', 
                          course_attendance=course_attendance)

@attendance.route('/teacher/course/create', methods=['GET', 'POST'])
@login_required
def create_course():
    if not current_user.is_teacher:
        flash('Access denied: You are not a teacher', 'danger')
        return redirect(url_for('attendance.student_dashboard'))
    
    form = CourseForm()
    if form.validate_on_submit():
        existing_course = Course.query.filter_by(code=form.code.data).first()
        if existing_course:
            flash(f'Course code {form.code.data} already exists', 'danger')
        else:
            course = Course(
                name=form.name.data,
                code=form.code.data,
                teacher_id=current_user.id
            )
            db.session.add(course)
            db.session.commit()
            flash(f'Course "{form.name.data}" has been created', 'success')
            return redirect(url_for('attendance.teacher_dashboard'))
    
    return render_template('create_course.html', form=form, title='Create Course')

@attendance.route('/teacher/course/<int:course_id>')
@login_required
def course_details(course_id):
    if not current_user.is_teacher:
        flash('Access denied: You are not a teacher', 'danger')
        return redirect(url_for('attendance.student_dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verify the teacher owns this course
    if course.teacher_id != current_user.id:
        flash('Access denied: This is not your course', 'danger')
        return redirect(url_for('attendance.teacher_dashboard'))
    
    # Get attendance sessions for this course
    sessions = AttendanceSession.query.filter_by(course_id=course_id).order_by(AttendanceSession.date.desc()).all()
    
    # Get enrolled students
    enrollments = StudentCourse.query.filter_by(course_id=course_id).all()
    students = [User.query.get(e.student_id) for e in enrollments]
    
    return render_template('course_details.html', 
                          title=f'Course: {course.name}',
                          course=course,
                          sessions=sessions,
                          students=students)

@attendance.route('/teacher/take-attendance/<int:course_id>', methods=['GET', 'POST'])
@login_required
def take_attendance(course_id):
    if not current_user.is_teacher:
        flash('Access denied: You are not a teacher', 'danger')
        return redirect(url_for('attendance.student_dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verify the teacher owns this course
    if course.teacher_id != current_user.id:
        flash('Access denied: This is not your course', 'danger')
        return redirect(url_for('attendance.teacher_dashboard'))
    
    if request.method == 'POST':
        now = datetime.now()
        # Create a new attendance session
        session = AttendanceSession(
            course_id=course_id,
            date=date.today(),
            start_time=now.time()
        )
        db.session.add(session)
        db.session.commit()
        
        # Get the image data from the request
        image_data = request.json.get('imageData', '')
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data received'})
        
        # Remove the data:image/jpeg;base64, prefix
        image_data = image_data.split(',')[1]
        
        # Convert the base64 string to an image
        image_bytes = base64.b64decode(image_data)
        image_io = io.BytesIO(image_bytes)
        
        # Detect faces in the image
        try:
            face_encodings = detect_faces_from_image(image_io)
            
            # Get all students enrolled in this course
            enrollments = StudentCourse.query.filter_by(course_id=course_id).all()
            student_ids = [e.student_id for e in enrollments]
            students = User.query.filter(User.id.in_(student_ids)).all()
            
            # Dictionary to track which students were detected
            detected_students = {}
            
            # Compare faces with student encodings
            for student in students:
                if student.face_encoding is not None:
                    is_present = False
                    for face_encoding in face_encodings:
                        match = compare_faces(student.face_encoding, face_encoding)
                        if match:
                            is_present = True
                            break
                    
                    # Create an attendance record
                    attendance_record = Attendance(
                        student_id=student.id,
                        session_id=session.id,
                        is_present=is_present
                    )
                    db.session.add(attendance_record)
                    
                    detected_students[student.username] = is_present
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'session_id': session.id,
                'detected_students': detected_students
            })
            
        except Exception as e:
            logging.error(f"Error processing attendance: {str(e)}")
            return jsonify({'success': False, 'message': f'Error processing image: {str(e)}'})
    
    return render_template('capture.html', 
                          title=f'Take Attendance - {course.name}',
                          course=course)

@attendance.route('/student/enroll', methods=['GET', 'POST'])
@login_required
def enroll_in_course():
    if current_user.is_teacher:
        flash('Access denied: Teachers cannot enroll in courses', 'danger')
        return redirect(url_for('attendance.teacher_dashboard'))
    
    if request.method == 'POST':
        course_code = request.form.get('course_code')
        if not course_code:
            flash('Please enter a course code', 'danger')
            return redirect(url_for('attendance.enroll_in_course'))
        
        course = Course.query.filter_by(code=course_code).first()
        if not course:
            flash(f'Course with code {course_code} not found', 'danger')
            return redirect(url_for('attendance.enroll_in_course'))
        
        # Check if already enrolled
        existing_enrollment = StudentCourse.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        
        if existing_enrollment:
            flash(f'You are already enrolled in {course.name}', 'warning')
            return redirect(url_for('attendance.student_dashboard'))
        
        # Create enrollment
        enrollment = StudentCourse(
            student_id=current_user.id,
            course_id=course.id
        )
        db.session.add(enrollment)
        db.session.commit()
        
        flash(f'Successfully enrolled in {course.name}', 'success')
        return redirect(url_for('attendance.student_dashboard'))
    
    return render_template('enroll_course.html', title='Enroll in Course')

@attendance.route('/student/register-face', methods=['GET', 'POST'])
@login_required
def register_face():
    if current_user.is_teacher:
        flash('Access denied: Teachers do not need face registration', 'danger')
        return redirect(url_for('attendance.teacher_dashboard'))
    
    if request.method == 'POST':
        image_data = request.json.get('imageData', '')
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data received'})
        
        # Remove the data:image/jpeg;base64, prefix
        image_data = image_data.split(',')[1]
        
        # Convert the base64 string to an image
        image_bytes = base64.b64decode(image_data)
        image_io = io.BytesIO(image_bytes)
        
        try:
            face_encodings = detect_faces_from_image(image_io)
            
            if not face_encodings:
                return jsonify({
                    'success': False, 
                    'message': 'No face detected in the image. Please try again.'
                })
            
            if len(face_encodings) > 1:
                return jsonify({
                    'success': False, 
                    'message': 'Multiple faces detected. Please provide an image with only your face.'
                })
            
            # Store the face encoding for the current user
            current_user.set_face_encoding(face_encodings[0])
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Face registered successfully!'
            })
            
        except Exception as e:
            logging.error(f"Error registering face: {str(e)}")
            return jsonify({
                'success': False, 
                'message': f'Error processing image: {str(e)}'
            })
    
    return render_template('register_face.html', title='Register Your Face')

@attendance.route('/view-attendance/<int:course_id>')
@login_required
def view_attendance(course_id):
    course = Course.query.get_or_404(course_id)
    
    if current_user.is_teacher:
        # Ensure the teacher owns this course
        if course.teacher_id != current_user.id:
            flash('Access denied: This is not your course', 'danger')
            return redirect(url_for('attendance.teacher_dashboard'))
        
        # Get all sessions for this course
        sessions = AttendanceSession.query.filter_by(course_id=course_id).order_by(AttendanceSession.date).all()
        
        # Get all students enrolled in this course
        enrollments = StudentCourse.query.filter_by(course_id=course_id).all()
        students = [User.query.get(e.student_id) for e in enrollments]
        
        # Build attendance matrix for all students across all sessions
        attendance_matrix = []
        for student in students:
            student_attendance = []
            present_count = 0
            
            for session in sessions:
                attendance_record = Attendance.query.filter_by(
                    student_id=student.id,
                    session_id=session.id
                ).first()
                
                is_present = attendance_record and attendance_record.is_present
                if is_present:
                    present_count += 1
                
                student_attendance.append({
                    'session_id': session.id,
                    'is_present': is_present
                })
            
            # Calculate attendance percentage
            attendance_percentage = 0
            if sessions:
                attendance_percentage = (present_count / len(sessions)) * 100
            
            attendance_matrix.append({
                'student': student,
                'attendance': student_attendance,
                'present_count': present_count,
                'total_sessions': len(sessions),
                'percentage': round(attendance_percentage, 2)
            })
        
        return render_template('view_attendance.html', 
                              title=f'Attendance for {course.name}',
                              course=course,
                              sessions=sessions,
                              attendance_matrix=attendance_matrix,
                              is_teacher=True)
    else:
        # For students, verify they are enrolled in the course
        enrollment = StudentCourse.query.filter_by(
            student_id=current_user.id,
            course_id=course_id
        ).first()
        
        if not enrollment:
            flash('Access denied: You are not enrolled in this course', 'danger')
            return redirect(url_for('attendance.student_dashboard'))
        
        # Get all sessions for this course
        sessions = AttendanceSession.query.filter_by(course_id=course_id).order_by(AttendanceSession.date).all()
        
        # Get the student's attendance records
        student_attendance = []
        present_count = 0
        
        for session in sessions:
            attendance_record = Attendance.query.filter_by(
                student_id=current_user.id,
                session_id=session.id
            ).first()
            
            is_present = attendance_record and attendance_record.is_present
            if is_present:
                present_count += 1
            
            student_attendance.append({
                'session': session,
                'is_present': is_present
            })
        
        # Calculate attendance percentage
        attendance_percentage = 0
        if sessions:
            attendance_percentage = (present_count / len(sessions)) * 100
        
        return render_template('view_attendance.html', 
                              title=f'Your Attendance for {course.name}',
                              course=course,
                              student_attendance=student_attendance,
                              present_count=present_count,
                              total_sessions=len(sessions),
                              percentage=round(attendance_percentage, 2),
                              is_teacher=False)
