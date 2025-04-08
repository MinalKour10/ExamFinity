from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from datetime import datetime

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Sign Up')

class QuestionBankForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description')
    submit = SubmitField('Create Question Bank')

class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question Text', validators=[DataRequired()])
    question_type = SelectField('Question Type', 
                               choices=[('mcq', 'Multiple Choice'), 
                                        ('short_answer', 'Short Answer'), 
                                        ('essay', 'Essay'),
                                        ('true_false', 'True/False')],
                               default='mcq',
                               validators=[DataRequired()])
    option_a = TextAreaField('Option A')
    option_b = TextAreaField('Option B')
    option_c = TextAreaField('Option C')
    option_d = TextAreaField('Option D')
    correct_answer = TextAreaField('Correct Answer/Answer Key')
    answer_explanation = TextAreaField('Answer Explanation (Optional)')
    points = IntegerField('Points', default=1)
    submit = SubmitField('Add Question')

class ExamForm(FlaskForm):
    title = StringField('Exam Title', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description')
    duration_minutes = IntegerField('Duration (minutes)', validators=[DataRequired()])
    question_bank_id = SelectField('Question Bank', coerce=int, validators=[DataRequired()])
    scheduled_date = DateTimeField('Scheduled Date and Time', 
                                  format='%Y-%m-%d %H:%M',
                                  validators=[DataRequired()])
    submit = SubmitField('Schedule Exam')
    
    def validate_scheduled_date(self, scheduled_date):
        # First check if we have valid data
        if not scheduled_date.data:
            raise ValidationError('Please provide a valid date and time')
            
        # Check if the date is in the future
        if scheduled_date.data < datetime.now():
            raise ValidationError('Scheduled date must be in the future')
