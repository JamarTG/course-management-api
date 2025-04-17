from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

# ---------------------- Models ---------------------- #
class User(db.Model):
    __tablename__ = 'user' 
    userid = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('student', 'lecturer', 'admin'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))

class Course(db.Model):
    __tablename__ = 'course'  
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(255))
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.userid'))

class Course_Registration(db.Model):
    __tablename__ = 'course_registration'  
    stud_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'), primary_key=True)

class Assignment(db.Model):
    __tablename__ = 'assignment'
    assign_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)

class Submission(db.Model):
    __tablename__ = 'submission'
    assign_id = db.Column(db.Integer, db.ForeignKey('assignment.assign_id'), primary_key=True)
    stud_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    grade = db.Column(db.Numeric(5, 2))
    submission_url = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class Calendar_Event(db.Model):
    __tablename__ = 'calendar_event' 
    event_id = db.Column(db.Integer, primary_key=True)
    event_title = db.Column(db.String(255))
    event_date = db.Column(db.String(50))
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))

class Section(db.Model):
    __tablename__ = 'section'
    section_id = db.Column(db.Integer, primary_key=True)
    section_title = db.Column(db.String(255), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))

class Course_Content(db.Model):
    __tablename__ = 'course_content'
    content_id = db.Column(db.Integer, primary_key=True)
    content_title = db.Column(db.String(255))
    content_url = db.Column(db.String(255))
    content_type = db.Column(db.Enum('link', 'file', 'slide', name='content_types'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))
    section_id = db.Column(db.Integer, db.ForeignKey('section.section_id'))
    
class Forum(db.Model):
    __tablename__ = 'forum' 
    forum_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))
    forum_title = db.Column(db.String(255), nullable=False) 

class Discussion_Thread(db.Model):
    __tablename__ = 'discussion_thread'  
    thread_id = db.Column(db.Integer, primary_key=True)
    dis_title = db.Column(db.String(255))
    forum_id = db.Column(db.Integer, db.ForeignKey('forum.forum_id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.userid'))


class Thread_Reply(db.Model):
    __tablename__ = 'thread_reply'  
    reply_id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('discussion_thread.thread_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.userid'))
    reply_text = db.Column(db.Text)
    replied_at = db.Column(db.DateTime, server_default=func.now())


# Register User

@app.route('/register', methods=['POST'])
def register():
    data = request.json

    if not all(field in data for field in ['password', 'role', 'name']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    if data['role'] not in ['student', 'lecturer', 'admin']:
        return jsonify({'message': 'Invalid role. Must be student, lecturer, or admin'}), 400

    sql = text("SELECT * FROM user WHERE name = :name")
    existing_user = db.session.execute(sql, {'name': data.get('name')}).fetchone()

    if existing_user:
        return jsonify({'message': 'User already exists'}), 400

    try:
        sql = text("INSERT INTO user (password, role, name, email) VALUES (:password, :role, :name, :email)")
        db.session.execute(sql, {
            'password': data.get('password'),
            'role': data.get('role'),
            'name': data.get('name'),
            'email': data.get('email', '')
        })
        db.session.commit()

        last_inserted_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

        return jsonify({ 
            'message': 'User registered successfully', 
            'user': {
                'userid': last_inserted_id,  
                'name': data.get('name'),
                'role': data.get('role'),
                'email': data.get('email', '')
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500


# User Login

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if not data.get('userid') or not data.get('password'):
        return jsonify({'message': 'User ID and password are required'}), 400

    try:
        sql = text("SELECT * FROM user WHERE userid = :userid AND password = :password")
        user = db.session.execute(sql, {'userid': data['userid'], 'password': data['password']}).fetchone()

        if user:
            return jsonify({'message': 'Login successful', 'role': user[2]})  
        return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'message': 'An error occurred during login', 'error': str(e)}), 500


# Create Course

@app.route('/courses', methods=['POST'])
def create_course():
    data = request.json
    
    sql = text("SELECT * FROM user WHERE userid = :userid")
    admin = db.session.execute(sql, {'userid': data['userid']}).fetchone()
    if not admin or admin[2] != 'admin':  
        return jsonify({'message': 'Only admins can create courses'}), 403
    
    sql = text("SELECT * FROM user WHERE userid = :lecturer_id")
    lecturer = db.session.execute(sql, {'lecturer_id': data['lecturer_id']}).fetchone()
    if not lecturer or lecturer[2] != 'lecturer': 
        return jsonify({'message': 'Invalid lecturer. Please provide a valid user with a lecturer role.'}), 400

    sql = text("INSERT INTO course (course_name, lecturer_id) VALUES (:course_name, :lecturer_id)")
    db.session.execute(sql, {
        'course_name': data['course_name'],
        'lecturer_id': data['lecturer_id']
    })
    db.session.commit()

    sql = text("SELECT LAST_INSERT_ID()")
    course_id = db.session.execute(sql).fetchone()[0]

    return jsonify({'message': 'Course created', 'course_id': course_id})

# Retrieve Courses

@app.route('/courses', methods=['GET'])
def get_courses():
    sql = text("SELECT course_id, course_name FROM course")
    result = db.session.execute(sql).fetchall()
    return jsonify([{'course_id': row[0], 'course_name': row[1]} for row in result])

@app.route('/courses/student/<int:userid>', methods=['GET'])
def get_student_courses(userid):
    sql = text("SELECT * FROM user WHERE userid = :userid")
    result = db.session.execute(sql, {'userid': userid}).fetchone()
    
    if not result:
        return jsonify({'message': 'User not found'}), 404
    

    if result[2] != 'student': 
        return jsonify({'message': 'Only students can access this route'}), 403

    sql = text("SELECT course_id FROM course_registration WHERE stud_id = :userid")
    registrations = db.session.execute(sql, {'userid': userid}).fetchall()
    course_ids = [reg[0] for reg in registrations]  # Access course_id by index

    sql = text("SELECT course_id, course_name FROM course WHERE course_id IN :course_ids")
    courses = db.session.execute(sql, {'course_ids': tuple(course_ids)}).fetchall()

    return jsonify([{'course_id': row[0], 'course_name': row[1]} for row in courses])

@app.route('/courses/lecturer/<int:userid>', methods=['GET'])
def get_lecturer_courses(userid):
    sql = text("SELECT * FROM user WHERE userid = :userid")
    user = db.session.execute(sql, {'userid': userid}).fetchone()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    if user[2] != 'lecturer':
        return jsonify({'message': 'Only lecturers can access this route'}), 403

    sql = text("SELECT course_id, course_name FROM course WHERE lecturer_id = :userid")
    courses = db.session.execute(sql, {'userid': userid}).fetchall()

    return jsonify([{'course_id': course[0], 'course_name': course[1]} for course in courses])


# Register for Course

@app.route('/register-student', methods=['POST'])
def register_course():
    data = request.json
    
    if not all(field in data for field in ['stud_id', 'course_id']):
        return jsonify({'message': 'Missing stud_id or course_id'}), 400
    
    sql = text("SELECT * FROM user WHERE userid = :stud_id")
    user = db.session.execute(sql, {'stud_id': data['stud_id']}).fetchone()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if user[2] != 'student':  # Assuming the role is at index 2
        return jsonify({'message': 'Only students can register for courses'}), 403
    
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': data['course_id']}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    sql = text("INSERT INTO course_registration (stud_id, course_id) VALUES (:stud_id, :course_id)")
    db.session.execute(sql, {'stud_id': data['stud_id'], 'course_id': data['course_id']})
    db.session.commit()
    
    return jsonify({'message': 'Student successfully registered for the course'})


@app.route('/register-lecturer', methods=['POST'])
def register_lecturer():
    data = request.json
    
    if not all(field in data for field in ['lecturer_id', 'course_id']):
        return jsonify({'message': 'Missing lecturer_id or course_id'}), 400
    
    sql = text("SELECT * FROM user WHERE userid = :lecturer_id")
    user = db.session.execute(sql, {'lecturer_id': data['lecturer_id']}).fetchone()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if user[2] != 'lecturer':  # Assuming the role is at index 2
        return jsonify({'message': 'Only lecturers can register for courses'}), 403
    
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': data['course_id']}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    sql = text("INSERT INTO course_registration (stud_id, course_id) VALUES (:lecturer_id, :course_id)")
    db.session.execute(sql, {'lecturer_id': data['lecturer_id'], 'course_id': data['course_id']})
    db.session.commit()
    
    return jsonify({'message': 'Lecturer successfully registered for the course'})


# Retrieve Members

@app.route('/course-members/<int:course_id>', methods=['GET'])
def get_course_members(course_id):
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': course_id}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    lecturer_id = course[2]
    sql = text("SELECT userid, name, email FROM user WHERE userid = :lecturer_id")
    lecturer = db.session.execute(sql, {'lecturer_id': lecturer_id}).fetchone()
    
    if not lecturer:
        return jsonify({'message': 'Lecturer not found'}), 404
    
    sql = text("SELECT stud_id FROM course_registration WHERE course_id = :course_id")
    students = db.session.execute(sql, {'course_id': course_id}).fetchall()
    
    student_list = []
    for student in students:
        sql = text("SELECT userid, name, email FROM user WHERE userid = :stud_id")
        student_data = db.session.execute(sql, {'stud_id': student[0]}).fetchone()
        
        if student_data:
            student_list.append({
                'student_id': student_data[0],
                'name': student_data[1],
                'email': student_data[2]
            })
    
    return jsonify({
        'message': 'Course members retrieved successfully',
        'lecturer': {
            'lecturer_id': lecturer[0],
            'name': lecturer[1],
            'email': lecturer[2]
        },
        'students': student_list
    })

# Create Calendar Events


@app.route('/calendar', methods=['POST'])
def create_event():
    data = request.json

    if not all(field in data for field in ['event_title', 'event_date', 'course_id']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': data['course_id']}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    sql = text("INSERT INTO calendar_event (event_title, event_date, course_id) VALUES (:event_title, :event_date, :course_id)")
    db.session.execute(sql, {
        'event_title': data['event_title'],
        'event_date': data['event_date'],
        'course_id': data['course_id']
    })
    db.session.commit()

    return jsonify({'message': 'Event created successfully'})


# Forums - This part includes both fetching and posting for a course
@app.route('/forum/<int:course_id>', methods=['GET', 'POST'])
def forum(course_id):
    if request.method == 'GET':
        
        sql = text("SELECT forum_id, forum_title FROM forum WHERE course_id = :course_id")
        result = db.session.execute(sql, {'course_id': course_id}).fetchall()
        return jsonify([{'forum_id': row[0], 'forum_title': row[1]} for row in result])

    data = request.json
    forum_title = data.get('forum_title') 

    if not forum_title:
        return jsonify({'error': 'Forum title is required'}), 400

    sql = text("INSERT INTO forum (course_id, forum_title) VALUES (:course_id, :forum_title)")
    db.session.execute(sql, {'course_id': course_id, 'forum_title': forum_title})
    db.session.commit()

    forum_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

    return jsonify({'message': 'Forum created', 'forum_id': forum_id, 'forum_title': forum_title})

# Discussion Thread

@app.route('/threads/<int:forum_id>', methods=['GET', 'POST'])
def threads(forum_id):
    if request.method == 'GET':
        sql = text("SELECT thread_id, dis_title FROM discussion_thread WHERE forum_id = :forum_id")
        result = db.session.execute(sql, {'forum_id': forum_id}).fetchall()
        return jsonify([{'thread_id': row[0], 'dis_title': row[1]} for row in result])

    data = request.json
    sql = text("INSERT INTO discussion_thread (forum_id, dis_title, created_by) VALUES (:forum_id, :dis_title, :created_by)")
    db.session.execute(sql, {
        'forum_id': forum_id,
        'dis_title': data['dis_title'],
        'created_by': data['created_by']
    })
    db.session.commit()

    thread_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

    return jsonify({'message': 'Thread added', 'thread_id': thread_id})


@app.route('/threads/<int:thread_id>/replies', methods=['POST'])
def add_reply(thread_id):
    data = request.json
    sql = text("""
        INSERT INTO thread_reply (thread_id, user_id, reply_text, parent_reply_id)
        VALUES (:thread_id, :user_id, :reply_text, :parent_reply_id)
    """)
    db.session.execute(sql, {
        'thread_id': thread_id,  # changed from comment_id to thread_id
        'user_id': data['user_id'],
        'reply_text': data['reply_text'],
        'parent_reply_id': data.get('parent_reply_id')  # allows for nested replies
    })
    db.session.commit()
    return jsonify({'message': 'Reply added'})


# Course Content


# Use the following command below to create a section for testing

# INSERT INTO section (section_id, section_title, course_id)
# VALUES (1, 'Week 1 - Introduction', 1);

# There is no requirement to add a section endpoint so I didn't want to complicate things
# Could've added it as a property but I think making it a table is a better design choice


@app.route('/content/<int:course_id>', methods=['GET', 'POST'])
def course_content(course_id):
    
    userid = request.json.get('userid')

    if not userid:
        return jsonify({'error': 'User ID is required'}), 400

    lecturer_sql = text("""
        SELECT lecturer_id 
        FROM course 
        WHERE course_id = :course_id
    """)
    lecturer_id = db.session.execute(lecturer_sql, {'course_id': course_id}).scalar()

    if lecturer_id != userid:
        return jsonify({'error': 'Unauthorized. Only the lecturer of this course can add content.'}), 403

    if request.method == 'GET':
        sql = text("""
            SELECT content_title, content_url, content_type, section_id 
            FROM course_content 
            WHERE course_id = :course_id
        """)
        result = db.session.execute(sql, {'course_id': course_id}).mappings().fetchall()
        return jsonify([{
            'content_title': row['content_title'],
            'content_url': row['content_url'],
            'content_type': row['content_type'],
            'section_id': row['section_id']
        } for row in result])

    data = request.json
    section_check_sql = text("""
        SELECT COUNT(*) 
        FROM section 
        WHERE section_id = :section_id
    """)
    section_exists = db.session.execute(section_check_sql, {'section_id': data['section_id']}).scalar()

    if section_exists == 0:
        return jsonify({'error': f"Section with ID {data['section_id']} does not exist."}), 400

    sql = text("""
        INSERT INTO course_content (content_title, content_url, content_type, section_id, course_id) 
        VALUES (:content_title, :content_url, :content_type, :section_id, :course_id)
    """)
    db.session.execute(sql, {
        'content_title': data['content_title'],
        'content_url': data['content_url'],
        'content_type': data['content_type'],
        'section_id': data['section_id'],
        'course_id': course_id
    })
    db.session.commit()
    return jsonify({'message': 'Course content added'})

# Assignments

# Use the SQL command below to add an assignment
# INSERT INTO assignment (course_id, title, description, due_date)
# VALUES (1, 'Midterm Project', 'Build a web app', '2025-05-01 23:59:00');


@app.route('/assignment/<int:assign_id>/submit', methods=['POST'])
def submit_assignment(assign_id):
    student_id = request.json.get('student_id') 
    submission_url = request.json.get('submission_url')  

    assignment = db.session.query(Assignment).filter_by(assign_id=assign_id).first()
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404

    course_id = assignment.course_id
    enrollment_sql = text("""
        SELECT 1 FROM course_registration
        WHERE stud_id = :student_id AND course_id = :course_id
    """)
    enrolled = db.session.execute(enrollment_sql, {'student_id': student_id, 'course_id': course_id}).fetchone()

    if not enrolled:
        return jsonify({'error': 'Student not enrolled in this course.'}), 403

    submission = Submission(
        assign_id=assign_id,
        stud_id=student_id,
        submission_url=submission_url
    )
    db.session.add(submission)
    db.session.commit()
    return jsonify({'message': 'Assignment submitted successfully.'}), 201

@app.route('/assignment/<int:assign_id>/grade', methods=['POST'])
def grade_assignment(assign_id):
    lecturer_id = request.json.get('lecturer_id')  
    student_id = request.json.get('student_id')    
    grade = request.json.get('grade')             


    lecturer_sql = text("""SELECT lecturer_id FROM course WHERE course_id = :course_id""")
    course_id = db.session.query(Assignment).filter_by(assign_id=assign_id).first().course_id
    course_lecturer = db.session.execute(lecturer_sql, {'course_id': course_id}).scalar()

    if lecturer_id != course_lecturer:
        return jsonify({'error': 'Unauthorized. Only the lecturer of this course can grade assignments.'}), 403

  
    submission = db.session.query(Submission).filter_by(assign_id=assign_id, stud_id=student_id).first()
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404

    if submission.grade is not None:
        return jsonify({'error': 'Assignment already graded'}), 400

    # Update the grade
    submission.grade = grade
    db.session.commit()

    return jsonify({'message': 'Grade submitted successfully.'}), 200


if __name__ == '__main__':
    app.run(debug=True)
