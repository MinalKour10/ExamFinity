from datetime import datetime
from app import db
from flask_login import UserMixin

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f"Role('{self.name}')"

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicitly set table name to avoid conflict with PostgreSQL 'user' table
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    answers = db.relationship('Answer', backref='user', lazy=True)
    question_banks = db.relationship('QuestionBank', backref='creator', lazy=True, 
                                    foreign_keys='QuestionBank.created_by')
    user_exams = db.relationship('UserExam', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role.name}')"

class QuestionBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='question_bank', lazy=True)
    exams = db.relationship('Exam', backref='question_bank', lazy=True)

    def __repr__(self):
        return f"QuestionBank('{self.title}')"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False, default='mcq')  # 'mcq', 'short_answer', 'essay', etc.
    option_a = db.Column(db.Text, nullable=True)  # Made nullable for non-MCQ questions
    option_b = db.Column(db.Text, nullable=True)  # Made nullable for non-MCQ questions
    option_c = db.Column(db.Text, nullable=True)  # Made nullable for non-MCQ questions
    option_d = db.Column(db.Text, nullable=True)  # Made nullable for non-MCQ questions
    correct_answer = db.Column(db.Text, nullable=True)  # Made nullable and Text type for longer answers
    answer_explanation = db.Column(db.Text, nullable=True)  # Added explanation for correct answers
    question_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.Column(db.Integer, default=1)  # Added points to assign different weights to questions
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True)

    def __repr__(self):
        return f"Question('{self.question_text[:30]}...', Type: {self.question_type})"

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False)
    question_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    answers = db.relationship('Answer', backref='exam', lazy=True)
    user_exams = db.relationship('UserExam', backref='exam', lazy=True)

    def __repr__(self):
        return f"Exam('{self.title}', '{self.scheduled_date}')"

class UserExam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    tab_switch_count = db.Column(db.Integer, default=0)
    
    # Webcam monitoring fields
    webcam_enabled = db.Column(db.Boolean, default=False)
    webcam_consent_given = db.Column(db.Boolean, default=False)
    webcam_status_message = db.Column(db.String(255), nullable=True)
    webcam_violation_count = db.Column(db.Integer, default=0)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'exam_id', name='_user_exam_uc'),
    )

    def __repr__(self):
        return f"UserExam(User: {self.user_id}, Exam: {self.exam_id}, Completed: {self.is_completed})"

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id', 'exam_id', name='_user_question_exam_uc'),
    )

    def __repr__(self):
        return f"Answer(User: {self.user_id}, Question: {self.question_id})"

class WebcamFrame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    user_exam_id = db.Column(db.Integer, db.ForeignKey('user_exam.id'), nullable=False)
    frame_data = db.Column(db.Text, nullable=False)  # Base64 encoded image data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.String(255), nullable=True)
    
    # Relationships
    user_exam = db.relationship('UserExam', backref='webcam_frames', lazy=True)
    
    def __repr__(self):
        return f"WebcamFrame(User: {self.user_id}, Exam: {self.exam_id}, Time: {self.timestamp})"
