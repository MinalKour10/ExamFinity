import os
import logging
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, flash, url_for, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect


# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create DeclarativeBase class
class Base(DeclarativeBase):
    pass

# Initialize Flask app and SQLAlchemy
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_for_testing")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL", "sqlite:///instance/exams.db")
# If using Heroku, fix the database URL if needed
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Make csrf_token and other useful variables available to all templates
@app.context_processor
def inject_template_vars():
    return {
        'csrf_token': lambda: csrf._get_csrf_token(),
        'now': datetime.now,
        'current_date': datetime.now(),  # Add the current date as a value, not a function
        'app_name': 'Online Examination System'
    }

# Import models after db initialization to avoid circular imports
with app.app_context():
    from models import User, Role, Exam, Question, Answer, QuestionBank, UserExam, WebcamFrame
    
    # Handle dropping and recreating tables with PostgreSQL
    try:
        # Drop existing tables that might conflict with our new schema
        with db.engine.connect() as conn:
            conn.execute(db.text("DROP TABLE IF EXISTS answer, user_exam, exam, question, question_bank, users, \"user\", role CASCADE"))
            conn.commit()
    except Exception as e:
        logging.error(f"Error dropping tables: {e}")
        # Continue even if there's an error
        pass
    
    # Create all tables with the new schema
    db.create_all()
    
    # Create default roles if they don't exist
    roles = ['admin', 'teacher', 'student']
    for role_name in roles:
        new_role = Role(name=role_name)
        db.session.add(new_role)
    
    db.session.commit()
    
    # Get admin role for creating default admin
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        # Create default admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123"),
            role_id=admin_role.id
        )
        db.session.add(admin)
        db.session.commit()

from forms import LoginForm, RegisterForm, QuestionBankForm, ExamForm, QuestionForm

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Login successful!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    
    # Get all roles for the select field
    form.role.choices = [(role.id, role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        # Check if username or email already exists
        user_exists = User.query.filter_by(username=form.username.data).first()
        email_exists = User.query.filter_by(email=form.email.data).first()
        
        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
        elif email_exists:
            flash('Email already registered. Please use a different one.', 'danger')
        else:
            # Create new user
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=hashed_password,
                role_id=form.role.data
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_role = current_user.role.name
    
    if user_role == 'student':
        # Get available exams for student
        available_exams = Exam.query.filter(
            Exam.scheduled_date > datetime.now() - timedelta(days=1)
        ).all()
        
        # Get already taken exams
        taken_exams = db.session.query(Exam).join(UserExam).filter(
            UserExam.user_id == current_user.id,
            UserExam.is_completed == True
        ).all()
        
        return render_template('dashboard.html', available_exams=available_exams, taken_exams=taken_exams)
    
    elif user_role == 'teacher':
        # Get question banks created by this teacher
        question_banks = QuestionBank.query.filter_by(created_by=current_user.id).all()
        
        # Get exams that use the teacher's question banks
        teacher_exams = Exam.query.filter(Exam.question_bank_id.in_([qb.id for qb in question_banks])).all()
        
        return render_template('dashboard.html', question_banks=question_banks, exams=teacher_exams)
    
    elif user_role == 'admin':
        # Get all exams and users for admin
        all_exams = Exam.query.all()
        all_users = User.query.all()
        
        return render_template('dashboard.html', exams=all_exams, users=all_users)
    
    return render_template('dashboard.html')

# Student routes
@app.route('/exams')
@login_required
def exams():
    if current_user.role.name != 'student':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get available exams for student
    available_exams = Exam.query.filter(
        Exam.scheduled_date > datetime.now() - timedelta(days=1)
    ).all()
    
    # Filter out already taken exams
    taken_exam_ids = [ue.exam_id for ue in UserExam.query.filter_by(user_id=current_user.id, is_completed=True).all()]
    available_exams = [exam for exam in available_exams if exam.id not in taken_exam_ids]
    
    return render_template('student/exams.html', exams=available_exams)

@app.route('/exam/<int:exam_id>/start', methods=['GET', 'POST'])
@login_required
def start_exam(exam_id):
    if current_user.role.name != 'student':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if exam exists
    exam = Exam.query.get_or_404(exam_id)
    
    # Check if exam is available
    if exam.scheduled_date > datetime.now():
        flash('This exam is not yet available.', 'danger')
        return redirect(url_for('exams'))
    
    # Check if the student has already taken this exam
    user_exam = UserExam.query.filter_by(user_id=current_user.id, exam_id=exam_id, is_completed=True).first()
    if user_exam:
        flash('You have already completed this exam.', 'info')
        return redirect(url_for('dashboard'))
    
    # Initialize or get in-progress user exam
    user_exam = UserExam.query.filter_by(user_id=current_user.id, exam_id=exam_id, is_completed=False).first()
    if not user_exam:
        user_exam = UserExam(
            user_id=current_user.id,
            exam_id=exam_id,
            start_time=datetime.now(),
            is_completed=False
        )
        db.session.add(user_exam)
        db.session.commit()
    
    # Get all questions for this exam
    questions = Question.query.filter_by(question_bank_id=exam.question_bank_id).all()
    
    if request.method == 'POST':
        # Record answers
        for question in questions:
            answer_text = request.form.get(f'question_{question.id}')
            if answer_text:
                # Check if answer already exists
                existing_answer = Answer.query.filter_by(
                    user_id=current_user.id,
                    question_id=question.id,
                    exam_id=exam_id
                ).first()
                
                if existing_answer:
                    existing_answer.answer_text = answer_text
                else:
                    answer = Answer(
                        user_id=current_user.id,
                        question_id=question.id,
                        exam_id=exam_id,
                        answer_text=answer_text
                    )
                    db.session.add(answer)
        
        # Check if this is an autosave request
        if request.form.get('autosave') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Answers saved successfully'})
        
        # Otherwise, it's a final submission
        user_exam.is_completed = True
        user_exam.end_time = datetime.now()
        db.session.commit()
        
        flash('Exam submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    # Create a form for CSRF protection
    from forms import FlaskForm
    form = FlaskForm()
    return render_template('student/take_exam.html', exam=exam, questions=questions, form=form)

@app.route('/exam/<int:exam_id>/tab-switch', methods=['POST'])
@login_required
def tab_switch(exam_id):
    if current_user.role.name != 'student':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    # Record tab switching attempt
    user_exam = UserExam.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    if user_exam:
        user_exam.tab_switch_count = (user_exam.tab_switch_count or 0) + 1
        db.session.commit()
        logging.warning(f"Tab switch detected for user {current_user.id} on exam {exam_id}")
    
    # You could implement additional penalties here
    
    return jsonify({'status': 'warning', 'message': 'Tab switching detected and recorded'})

@app.route('/results')
@login_required
def results():
    if current_user.role.name != 'student':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all completed exams for this student
    completed_exams = db.session.query(Exam).join(UserExam).filter(
        UserExam.user_id == current_user.id,
        UserExam.is_completed == True
    ).all()
    
    return render_template('student/results.html', exams=completed_exams)

# Teacher routes
@app.route('/question-banks')
@login_required
def question_banks():
    if current_user.role.name != 'teacher':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get question banks created by this teacher
    banks = QuestionBank.query.filter_by(created_by=current_user.id).all()
    
    return render_template('teacher/question_banks.html', question_banks=banks)

@app.route('/question-banks/create', methods=['GET', 'POST'])
@login_required
def create_question_bank():
    if current_user.role.name != 'teacher':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = QuestionBankForm()
    
    if form.validate_on_submit():
        # Create new question bank
        new_bank = QuestionBank(
            title=form.title.data,
            description=form.description.data,
            created_by=current_user.id
        )
        
        db.session.add(new_bank)
        db.session.commit()
        
        flash('Question bank created successfully!', 'success')
        return redirect(url_for('add_questions', bank_id=new_bank.id))
    
    return render_template('teacher/create_question_bank.html', form=form)

@app.route('/question-banks/<int:bank_id>/questions', methods=['GET', 'POST'])
@login_required
def add_questions(bank_id):
    if current_user.role.name != 'teacher':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if question bank exists and belongs to this teacher
    bank = QuestionBank.query.filter_by(id=bank_id, created_by=current_user.id).first_or_404()
    
    question_form = QuestionForm()
    bank_form = QuestionBankForm()
    
    # Populate bank form with existing values
    if request.method == 'GET':
        bank_form.title.data = bank.title
        bank_form.description.data = bank.description
    
    if question_form.validate_on_submit():
        # Add new question
        question_type = question_form.question_type.data
        
        # Create new question with all fields
        new_question = Question(
            question_text=question_form.question_text.data,
            question_type=question_type,
            question_bank_id=bank_id,
            points=question_form.points.data or 1,
            answer_explanation=question_form.answer_explanation.data
        )
        
        # Set MCQ options only if it's a multiple choice question
        if question_type == 'mcq':
            new_question.option_a = question_form.option_a.data
            new_question.option_b = question_form.option_b.data
            new_question.option_c = question_form.option_c.data
            new_question.option_d = question_form.option_d.data
        
        # Set correct answer
        new_question.correct_answer = question_form.correct_answer.data
        
        db.session.add(new_question)
        db.session.commit()
        
        flash('Question added successfully!', 'success')
        # Clear form data
        question_form.question_text.data = ''
        question_form.option_a.data = ''
        question_form.option_b.data = ''
        question_form.option_c.data = ''
        question_form.option_d.data = ''
        question_form.correct_answer.data = ''
        question_form.answer_explanation.data = ''
        # Reset points to default 1
        question_form.points.data = 1
        # Reset question type to default mcq
        question_form.question_type.data = 'mcq'
    
    # Get existing questions for this bank
    questions = Question.query.filter_by(question_bank_id=bank_id).all()
    
    return render_template('teacher/add_questions.html', form=question_form, bank_form=bank_form, bank=bank, questions=questions)

@app.route('/review-answers/<int:exam_id>')
@login_required
def review_answers(exam_id):
    if current_user.role.name != 'teacher':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get exam details
    exam = Exam.query.get_or_404(exam_id)
    
    # Check if the teacher created the question bank for this exam
    bank = QuestionBank.query.filter_by(id=exam.question_bank_id, created_by=current_user.id).first()
    if not bank:
        flash('You do not have permission to review this exam.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all students who took this exam
    students = db.session.query(User).join(UserExam).filter(
        UserExam.exam_id == exam_id,
        UserExam.is_completed == True
    ).all()
    
    # Get questions from this exam's question bank
    questions = Question.query.filter_by(question_bank_id=exam.question_bank_id).all()
    
    # Get all answers for this exam
    answers = Answer.query.filter_by(exam_id=exam_id).all()
    
    # Organize answers by student and question
    student_answers = {}
    for student in students:
        student_answers[student.id] = {
            'user': student,
            'answers': {},
            'tab_switches': UserExam.query.filter_by(user_id=student.id, exam_id=exam_id).first().tab_switch_count or 0
        }
        
        for question in questions:
            answer = next((a for a in answers if a.user_id == student.id and a.question_id == question.id), None)
            student_answers[student.id]['answers'][question.id] = {
                'question': question,
                'answer': answer.answer_text if answer else 'No answer provided',
                'is_correct': answer.answer_text == question.correct_answer if answer else False
            }
    
    return render_template('teacher/review_answers.html', exam=exam, student_answers=student_answers, questions=questions)

# Admin routes
@app.route('/schedule-exam', methods=['GET', 'POST'])
@login_required
def schedule_exam():
    if current_user.role.name != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = ExamForm()
    
    # Get all question banks for the select field
    form.question_bank_id.choices = [(qb.id, qb.title) for qb in QuestionBank.query.all()]
    
    if request.method == 'POST':
        # Log the form data for debugging
        logging.debug(f"Form data: {request.form}")
        
        # Check if scheduled_date is in the request form
        if 'scheduled_date' in request.form and request.form['scheduled_date']:
            try:
                # Try to parse the date manually
                date_str = request.form['scheduled_date']
                logging.debug(f"Received date string: {date_str}")
                
                # Attempt to parse using the format from the form
                scheduled_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                logging.debug(f"Parsed date: {scheduled_date}")
                
                # Override the form's data with the correctly parsed date
                form.scheduled_date.data = scheduled_date
            except ValueError as e:
                logging.error(f"Error parsing date: {e}")
                flash('Invalid date format. Please use YYYY-MM-DD HH:MM format.', 'danger')
    
    if form.validate_on_submit():
        try:
            # Create new exam
            new_exam = Exam(
                title=form.title.data,
                description=form.description.data,
                duration_minutes=form.duration_minutes.data,
                question_bank_id=form.question_bank_id.data,
                scheduled_date=form.scheduled_date.data
            )
            
            logging.debug(f"Created exam with scheduled_date: {new_exam.scheduled_date}")
        except Exception as e:
            logging.error(f"Error creating exam: {str(e)}")
            flash(f'Error creating exam: {str(e)}', 'danger')
            return render_template('admin/schedule_exam.html', form=form)
        
        db.session.add(new_exam)
        db.session.commit()
        
        flash('Exam scheduled successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('admin/schedule_exam.html', form=form)

@app.route('/manage-users')
@login_required
def manage_users():
    if current_user.role.name != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all users
    users = User.query.all()
    
    return render_template('admin/manage_users.html', users=users)

@app.route('/manage-users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    if current_user.role.name != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Don't allow deactivating own account
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('manage_users'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Webcam monitoring routes
@app.route('/exam/<int:exam_id>/webcam-frame', methods=['POST'])
@login_required
def webcam_frame(exam_id):
    if current_user.role.name != 'student':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    # Get user exam record
    user_exam = UserExam.query.filter_by(user_id=current_user.id, exam_id=exam_id, is_completed=False).first()
    if not user_exam:
        return jsonify({'status': 'error', 'message': 'No active exam found'}), 404
    
    # Parse request data
    data = request.get_json()
    if not data or 'imageData' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400
    
    # Store webcam frame
    frame = WebcamFrame(
        user_id=current_user.id,
        exam_id=exam_id,
        user_exam_id=user_exam.id,
        frame_data=data['imageData'],
        timestamp=datetime.now()
    )
    db.session.add(frame)
    
    # Update user_exam record
    user_exam.webcam_enabled = True
    db.session.commit()
    
    # Here you could implement AI analysis to detect unusual activities
    # For this implementation, we'll just store the frames
    
    return jsonify({'status': 'success', 'message': 'Frame received'})

@app.route('/exam/<int:exam_id>/webcam-status', methods=['POST'])
@login_required
def webcam_status(exam_id):
    if current_user.role.name != 'student':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    # Get user exam record
    user_exam = UserExam.query.filter_by(user_id=current_user.id, exam_id=exam_id, is_completed=False).first()
    if not user_exam:
        return jsonify({'status': 'error', 'message': 'No active exam found'}), 404
    
    # Parse request data
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400
    
    # Update webcam status
    user_exam.webcam_enabled = data.get('isEnabled', False)
    user_exam.webcam_status_message = data.get('message', None)
    
    # If webcam is disabled, count it as a violation
    if not user_exam.webcam_enabled and data.get('message', '').startswith('Webcam access denied'):
        user_exam.webcam_violation_count = (user_exam.webcam_violation_count or 0) + 1
        logging.warning(f"Webcam violation for user {current_user.id} on exam {exam_id}: {data.get('message')}")
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Status updated'})

@app.route('/exam/<int:exam_id>/webcam-consent', methods=['POST'])
@login_required
def webcam_consent(exam_id):
    if current_user.role.name != 'student':
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    # Get user exam record
    user_exam = UserExam.query.filter_by(user_id=current_user.id, exam_id=exam_id, is_completed=False).first()
    if not user_exam:
        return jsonify({'status': 'error', 'message': 'No active exam found'}), 404
    
    # Parse request data
    data = request.get_json()
    if not data or 'consent' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400
    
    # Update webcam consent
    user_exam.webcam_consent_given = data['consent']
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Consent recorded'})

# Teacher/admin webcam frame review route
@app.route('/review-webcam/<int:user_exam_id>')
@login_required
def review_webcam(user_exam_id):
    # Only teachers and admins can review webcam frames
    if current_user.role.name not in ['teacher', 'admin']:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get user exam
    user_exam = UserExam.query.get_or_404(user_exam_id)
    
    # For teachers, check if they own the question bank
    if current_user.role.name == 'teacher':
        exam = Exam.query.get_or_404(user_exam.exam_id)
        bank = QuestionBank.query.filter_by(id=exam.question_bank_id, created_by=current_user.id).first()
        if not bank:
            flash('You do not have permission to view this data.', 'danger')
            return redirect(url_for('dashboard'))
    
    # Get webcam frames for this user exam
    frames = WebcamFrame.query.filter_by(user_exam_id=user_exam_id).order_by(WebcamFrame.timestamp).all()
    
    # Get student and exam info
    student = User.query.get_or_404(user_exam.user_id)
    exam = Exam.query.get_or_404(user_exam.exam_id)
    
    return render_template('review_webcam.html', frames=frames, user_exam=user_exam, student=student, exam=exam)
