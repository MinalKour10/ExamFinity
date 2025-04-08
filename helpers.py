import datetime
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(roles):
    """
    Decorator to check if the current user has the required role
    :param roles: A string or list of roles that are allowed to access the route
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            
            if isinstance(roles, str):
                role_list = [roles]
            else:
                role_list = roles
                
            if current_user.role.name not in role_list:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def format_datetime(dt):
    """Format datetime object into a readable string"""
    if not dt:
        return "N/A"
    return dt.strftime("%b %d, %Y %I:%M %p")

def calculate_exam_status(exam):
    """
    Calculate the status of an exam based on its scheduled date
    :return: String status ('upcoming', 'active', or 'expired')
    """
    now = datetime.datetime.now()
    
    if exam.scheduled_date > now:
        return 'upcoming'
    elif exam.scheduled_date <= now and exam.scheduled_date + datetime.timedelta(minutes=exam.duration_minutes) >= now:
        return 'active'
    else:
        return 'expired'

def calculate_score(user_id, exam_id):
    """
    Calculate a user's score for a specific exam
    :return: Tuple (score, total_questions)
    """
    from models import Question, Answer
    
    # Get all questions for this exam
    questions = Question.query.filter_by(exam_id=exam_id).all()
    total_questions = len(questions)
    
    if total_questions == 0:
        return 0, 0
    
    # Get all answers for this user and exam
    answers = Answer.query.filter_by(user_id=user_id, exam_id=exam_id).all()
    
    # Count correct answers
    correct_count = 0
    for answer in answers:
        question = Question.query.get(answer.question_id)
        if answer.answer_text == question.correct_answer:
            correct_count += 1
    
    return correct_count, total_questions








main.py 
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
