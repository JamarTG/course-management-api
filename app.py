from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

# We're not using ORM models, keeping this import for the db connection and text query execution only

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
        hashed_password = generate_password_hash(data['password'])

        sql = text("INSERT INTO user (password, role, name, email) VALUES (:password, :role, :name, :email)")
        db.session.execute(sql, {
            'password': hashed_password,
            'role': data['role'],
            'name': data['name'],
            'email': data.get('email', '')
        })
        db.session.commit()

        last_inserted_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'userid': last_inserted_id,
                'name': data['name'],
                'role': data['role'],
                'email': data.get('email', '')
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if not data.get('userid') or not data.get('password'):
        return jsonify({'message': 'User ID and password are required'}), 400

    try:
        sql = text("SELECT * FROM user WHERE userid = :userid")
        user = db.session.execute(sql, {'userid': data['userid']}).fetchone()

        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401

        if check_password_hash(user.password, data['password']):  
            return jsonify({
                'message': 'Login successful',
                'role': user.role  
            })

        return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'message': 'An error occurred during login', 'error': str(e)}), 500


@app.route('/courses', methods=['POST'])
def create_course():
    data = request.json

    sql = text("SELECT * FROM user WHERE userid = :userid")
    admin = db.session.execute(sql, {'userid': data['userid']}).fetchone()
    if not admin or admin[2] != 'admin':  
        return jsonify({'message': 'Only admins can create courses'}), 403

    lecturer_id = data.get('lecturer_id')

    if lecturer_id is not None:
        sql = text("SELECT * FROM user WHERE userid = :lecturer_id")
        lecturer = db.session.execute(sql, {'lecturer_id': lecturer_id}).fetchone()
        if not lecturer or lecturer[2] != 'lecturer': 
            return jsonify({'message': 'Invalid lecturer. Please provide a valid user with a lecturer role.'}), 400

    sql = text("INSERT INTO course (course_name, lecturer_id) VALUES (:course_name, :lecturer_id)")
    db.session.execute(sql, {
        'course_name': data['course_name'],
        'lecturer_id': lecturer_id
    })
    db.session.commit()

    sql = text("SELECT LAST_INSERT_ID()")
    course_id = db.session.execute(sql).fetchone()[0]

    return jsonify({'message': 'Course created', 'course_id': course_id})


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

    sql = text("""
        SELECT c.course_id, c.course_name 
        FROM course c
        JOIN course_registration cr ON c.course_id = cr.course_id
        WHERE cr.stud_id = :userid
    """)
    
    courses = db.session.execute(sql, {'userid': userid}).fetchall()
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


@app.route('/register-student', methods=['POST'])
def register_course():
    data = request.json
    
    if not all(field in data for field in ['stud_id', 'course_id']):
        return jsonify({'message': 'Missing stud_id or course_id'}), 400
    
    sql = text("SELECT * FROM user WHERE userid = :stud_id")
    user = db.session.execute(sql, {'stud_id': data['stud_id']}).fetchone()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if user[2] != 'student':
        return jsonify({'message': 'Only students can register for courses'}), 403
    
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': data['course_id']}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    # Check if student is already registered for the course
    sql = text("""
        SELECT COUNT(*) FROM course_registration 
        WHERE stud_id = :stud_id AND course_id = :course_id
    """)
    exists = db.session.execute(sql, {
        'stud_id': data['stud_id'], 
        'course_id': data['course_id']
    }).scalar()
    
    if exists > 0:
        return jsonify({'message': 'Student already registered for the course'}), 400
    
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
    
    if user[2] != 'lecturer':
        return jsonify({'message': 'Only lecturers can register for courses'}), 403
    
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': data['course_id']}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404

    if course[2] == data['lecturer_id']:  
        return jsonify({'message': 'Lecturer is already registered for this course'}), 400

    sql = text("UPDATE course SET lecturer_id = :lecturer_id WHERE course_id = :course_id")
    db.session.execute(sql, {'lecturer_id': data['lecturer_id'], 'course_id': data['course_id']})
    db.session.commit()
    
    return jsonify({'message': 'Lecturer successfully registered for the course'})


@app.route('/course-members/<int:course_id>', methods=['GET'])
def get_course_members(course_id):
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': course_id}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    lecturer_info = None
    students = []

    # Fetch lecturer information
    if course[2]:  # If lecturer_id is not null
        sql = text("SELECT userid, name, email, role FROM user WHERE userid = :lecturer_id")
        lecturer = db.session.execute(sql, {'lecturer_id': course[2]}).fetchone()

        if lecturer and lecturer[3] == 'lecturer':
            lecturer_info = {
                'lecturer_id': lecturer[0],
                'name': lecturer[1],
                'email': lecturer[2]
            }
            
    sql = text("""
        SELECT u.userid, u.name, u.email
        FROM user u
        JOIN course_registration cr ON u.userid = cr.stud_id
        WHERE cr.course_id = :course_id AND u.role = 'student'
    """)
    student_results = db.session.execute(sql, {'course_id': course_id}).fetchall()
    
    for student in student_results:
        students.append({
            'student_id': student[0],
            'name': student[1],
            'email': student[2]
        })

    return jsonify({
        'message': 'Course members retrieved successfully',
        'lecturer': lecturer_info,
        'students': students
    })


@app.route('/calendar', methods=['POST'])
def create_event():
    data = request.json

    if not all(field in data for field in ['event_title', 'event_date', 'course_id']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': data['course_id']}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    sql = text("""
        INSERT INTO calendar_event (event_title, event_date, course_id) 
        VALUES (:event_title, :event_date, :course_id)
    """)
    db.session.execute(sql, {
        'event_title': data['event_title'],
        'event_date': data['event_date'],
        'course_id': data['course_id']
    })
    db.session.commit()

    return jsonify({'message': 'Event created successfully'})


@app.route('/calendar/course/<int:course_id>', methods=['GET'])
def get_course_events(course_id):
    sql = text("SELECT * FROM course WHERE course_id = :course_id")
    course = db.session.execute(sql, {'course_id': course_id}).fetchone()
    
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    sql = text("""
        SELECT event_id, event_title, event_date 
        FROM calendar_event
        WHERE course_id = :course_id
    """)
    events = db.session.execute(sql, {'course_id': course_id}).fetchall()
    
    event_list = []
    for event in events:
        event_list.append({
            'event_id': event[0],
            'event_title': event[1],
            'event_date': event[2]
        })
    
    return jsonify({'events': event_list})


@app.route('/calendar/student/<int:student_id>/<date>', methods=['GET'])
def get_student_events(student_id, date):
    sql = text("""
        SELECT ce.event_id, ce.event_title, ce.event_date, ce.course_id
        FROM calendar_event ce
        JOIN course_registration cr ON ce.course_id = cr.course_id
        WHERE cr.stud_id = :student_id AND ce.event_date = :date
    """)
    events = db.session.execute(sql, {'student_id': student_id, 'date': date}).fetchall()
    
    event_list = []
    for event in events:
        event_list.append({
            'event_id': event[0],
            'event_title': event[1],
            'event_date': event[2],
            'course_id': event[3]
        })
    
    return jsonify({'events': event_list})


@app.route('/forum/<int:course_id>', methods=['GET', 'POST'])
def forum(course_id):
    if request.method == 'GET':
        sql = text("SELECT forum_id, forum_title FROM forum WHERE course_id = :course_id")
        result = db.session.execute(sql, {'course_id': course_id}).fetchall()
        return jsonify([{'forum_id': row[0], 'forum_title': row[1]} for row in result])

    # POST method
    data = request.json
    forum_title = data.get('forum_title')

    if not forum_title:
        return jsonify({'error': 'Forum title is required'}), 400

    sql = text("INSERT INTO forum (course_id, forum_title) VALUES (:course_id, :forum_title)")
    db.session.execute(sql, {'course_id': course_id, 'forum_title': forum_title})
    db.session.commit()

    forum_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

    return jsonify({'message': 'Forum created', 'forum_id': forum_id, 'forum_title': forum_title})


@app.route('/threads/<int:forum_id>', methods=['GET', 'POST'])
def threads(forum_id):
    if request.method == 'GET':
        sql = text("""
            SELECT t.thread_id, t.dis_title, t.created_by, u.name as creator_name
            FROM discussion_thread t
            JOIN user u ON t.created_by = u.userid
            WHERE t.forum_id = :forum_id
        """)
        result = db.session.execute(sql, {'forum_id': forum_id}).fetchall()
        return jsonify([{
            'thread_id': row[0], 
            'dis_title': row[1],
            'created_by': row[2],
            'creator_name': row[3]
        } for row in result])

    # POST method
    data = request.json
    if not all(field in data for field in ['dis_title', 'created_by']):
        return jsonify({'error': 'Discussion title and creator ID are required'}), 400
    
    sql = text("""
        INSERT INTO discussion_thread (forum_id, dis_title, created_by) 
        VALUES (:forum_id, :dis_title, :created_by)
    """)
    db.session.execute(sql, {
        'forum_id': forum_id,
        'dis_title': data['dis_title'],
        'created_by': data['created_by']
    })
    db.session.commit()

    thread_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

    return jsonify({
        'message': 'Thread added', 
        'thread_id': thread_id,
        'dis_title': data['dis_title']
    })


@app.route('/threads/<int:thread_id>/replies', methods=['GET', 'POST'])
def thread_replies(thread_id):
    if request.method == 'GET':
        sql = text("""
            SELECT r.reply_id, r.user_id, u.name as user_name, r.reply_text, r.replied_at
            FROM thread_reply r
            JOIN user u ON r.user_id = u.userid
            WHERE r.thread_id = :thread_id
            ORDER BY r.replied_at ASC
        """)
        replies = db.session.execute(sql, {'thread_id': thread_id}).fetchall()
        
        return jsonify([{
            'reply_id': reply[0],
            'user_id': reply[1],
            'user_name': reply[2],
            'reply_text': reply[3],
            'replied_at': reply[4].isoformat() if reply[4] else None
        } for reply in replies])
    
    # POST method
    data = request.json
    if not all(field in data for field in ['user_id', 'reply_text']):
        return jsonify({'error': 'User ID and reply text are required'}), 400
    
    sql = text("SELECT * FROM discussion_thread WHERE thread_id = :thread_id")
    thread = db.session.execute(sql, {'thread_id': thread_id}).fetchone()
    
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404
    
    now = datetime.utcnow()
    
    sql = text("""
        INSERT INTO thread_reply (thread_id, user_id, reply_text, replied_at) 
        VALUES (:thread_id, :user_id, :reply_text, :replied_at)
    """)
    db.session.execute(sql, {
        'thread_id': thread_id,
        'user_id': data['user_id'],
        'reply_text': data['reply_text'],
        'replied_at': now
    })
    db.session.commit()
    
    reply_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
    
    return jsonify({
        'message': 'Reply added',
        'reply_id': reply_id,
        'replied_at': now.isoformat()
    })


@app.route('/content/<int:course_id>', methods=['GET', 'POST'])
def course_content(course_id):
    if request.method == 'GET':
        try:
            sql = text("""
                SELECT content_id, content_title, content_url, content_type, section_id 
                FROM course_content 
                WHERE course_id = :course_id
            """)
            result = db.session.execute(sql, {'course_id': course_id}).fetchall()
       
            if not result:
                return jsonify({'message': 'No content found for this course'}), 404

            content_list = []
            for row in result:
                content_list.append({
                    'content_id': row[0],
                    'content_title': row[1],
                    'content_url': row[2],
                    'content_type': row[3],
                    'section_id': row[4]
                })
            
            return jsonify({'content': content_list})

        except Exception as e:
            return jsonify({'error': f'Error fetching course content: {str(e)}'}), 500

    # POST method
    userid = request.json.get('userid')
    if not userid:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        lecturer_sql = text("""
            SELECT lecturer_id 
            FROM course 
            WHERE course_id = :course_id
        """)
        lecturer_id = db.session.execute(lecturer_sql, {'course_id': course_id}).scalar()

        if lecturer_id != userid:
            return jsonify({'error': 'Unauthorized. Only the lecturer of this course can add content.'}), 403

        data = request.json
        if not all(field in data for field in ['content_title', 'content_url', 'content_type', 'section_id']):
            return jsonify({'error': 'Missing required fields'}), 400

        # Sectin can be added here but it wasn't part of the requirements
      
        sql = text("""
            INSERT INTO course_content 
            (content_title, content_url, content_type, section_id, course_id) 
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

        content_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]

        return jsonify({
            'message': 'Course content added',
            'content_id': content_id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error adding course content: {str(e)}'}), 500


@app.route('/assignments/<int:course_id>', methods=['GET', 'POST'])
def assignments(course_id):
    if request.method == 'GET':
        sql = text("""
            SELECT assign_id, title, description, due_date 
            FROM assignment
            WHERE course_id = :course_id
        """)
        assignments = db.session.execute(sql, {'course_id': course_id}).fetchall()
        
        assignment_list = []
        for assignment in assignments:
            assignment_list.append({
                'assign_id': assignment[0],
                'title': assignment[1],
                'description': assignment[2],
                'due_date': assignment[3].isoformat() if assignment[3] else None
            })
        
        return jsonify({'assignments': assignment_list})
    
    # POST method (create new assignment)
    data = request.json
    lecturer_id = data.get('lecturer_id')
    
    if not lecturer_id:
        return jsonify({'error': 'Lecturer ID is required'}), 400
    
    # Check if lecturer is assigned to the course
    sql = text("SELECT lecturer_id FROM course WHERE course_id = :course_id")
    course_lecturer = db.session.execute(sql, {'course_id': course_id}).scalar()
    
    if course_lecturer != lecturer_id:
        return jsonify({'error': 'Unauthorized. Only the lecturer of this course can create assignments.'}), 403
    
    if not all(field in data for field in ['title', 'description', 'due_date']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    sql = text("""
        INSERT INTO assignment (course_id, title, description, due_date)
        VALUES (:course_id, :title, :description, :due_date)
    """)
    db.session.execute(sql, {
        'course_id': course_id,
        'title': data['title'],
        'description': data['description'],
        'due_date': data['due_date']
    })
    db.session.commit()
    
    assign_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
    
    return jsonify({
        'message': 'Assignment created successfully',
        'assign_id': assign_id
    })


@app.route('/assignment/<int:assign_id>/submit', methods=['POST'])
def submit_assignment(assign_id):
    data = request.json
    student_id = data.get('student_id')
    submission_url = data.get('submission_url')
    
    if not student_id or not submission_url:
        return jsonify({'error': 'Student ID and submission URL are required'}), 400
    
    # Check if assignment exists
    sql = text("SELECT course_id FROM assignment WHERE assign_id = :assign_id")
    assignment = db.session.execute(sql, {'assign_id': assign_id}).fetchone()
    
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404
    
    course_id = assignment[0]
    
    # Check if student is enrolled in the course
    sql = text("""
        SELECT 1 FROM course_registration
        WHERE stud_id = :student_id AND course_id = :course_id
    """)
    enrolled = db.session.execute(sql, {'student_id': student_id, 'course_id': course_id}).fetchone()
    
    if not enrolled:
        return jsonify({'error': 'Student not enrolled in this course.'}), 403
    
    # Check if student has already submitted this assignment
    sql = text("""
        SELECT 1 FROM submission
        WHERE assign_id = :assign_id AND stud_id = :student_id
    """)
    existing_submission = db.session.execute(sql, {
        'assign_id': assign_id, 
        'student_id': student_id
    }).fetchone()
    
    if existing_submission:
        return jsonify({'error': 'You have already submitted this assignment.'}), 400
    
    now = datetime.utcnow()
    
    sql = text("""
        INSERT INTO submission (assign_id, stud_id, submission_url, submitted_at)
        VALUES (:assign_id, :student_id, :submission_url, :submitted_at)
    """)
    db.session.execute(sql, {
        'assign_id': assign_id,
        'student_id': student_id,
        'submission_url': submission_url,
        'submitted_at': now
    })
    db.session.commit()
    
    return jsonify({'message': 'Assignment submitted successfully.'}), 201


@app.route('/assignment/<int:assign_id>/grade', methods=['POST'])
def grade_assignment(assign_id):
    data = request.json
    lecturer_id = data.get('lecturer_id')
    student_id = data.get('student_id')
    grade = data.get('grade')
    
    if not all([lecturer_id, student_id, grade is not None]):
        return jsonify({'error': 'Lecturer ID, student ID, and grade are required'}), 400
    
    # Check if lecturer is assigned to the course
    sql = text("""
        SELECT c.lecturer_id 
        FROM assignment a
        JOIN course c ON a.course_id = c.course_id
        WHERE a.assign_id = :assign_id
    """)
    course_lecturer = db.session.execute(sql, {'assign_id': assign_id}).scalar()
    
    if course_lecturer != lecturer_id:
        return jsonify({'error': 'Unauthorized. Only the lecturer of this course can grade assignments.'}), 403
    
    # Check if submission exists
    sql = text("""
        SELECT grade FROM submission
        WHERE assign_id = :assign_id AND stud_id = :student_id
    """)
    submission = db.session.execute(sql, {
        'assign_id': assign_id, 
        'student_id': student_id
    }).fetchone()
    
    if not submission:
        return jsonify({'error': 'Submission not found'}), 404
    
    if submission[0] is not None:
        return jsonify({'error': 'Assignment already graded'}), 400
    
    # Update the grade
    sql = text("""
        UPDATE submission
        SET grade = :grade
        WHERE assign_id = :assign_id AND stud_id = :student_id
    """)
    db.session.execute(sql, {
        'grade': grade,
        'assign_id': assign_id,
        'student_id': student_id
    })
    db.session.commit()
    
    return jsonify({'message': 'Grade submitted successfully.'}), 200


@app.route('/sections/<int:course_id>', methods=['GET', 'POST'])
def sections(course_id):
    if request.method == 'GET':
        sql = text("""
            SELECT section_id, section_title
            FROM section
            WHERE course_id = :course_id
            ORDER BY section_id
        """)
        sections = db.session.execute(sql, {'course_id': course_id}).fetchall()
        
        section_list = []
        for section in sections:
            section_list.append({
                'section_id': section[0],
                'section_title': section[1]
            })
        
        return jsonify({'sections': section_list})
    
    # POST method
    data = request.json
    lecturer_id = data.get('lecturer_id')
    section_title = data.get('section_title')
    
    if not lecturer_id or not section_title:
        return jsonify({'error': 'Lecturer ID and section title are required'}), 400
    
    # Check if lecturer is assigned to the course
    sql = text("SELECT lecturer_id FROM course WHERE course_id = :course_id")
    course_lecturer = db.session.execute(sql, {'course_id': course_id}).scalar()
    
    if course_lecturer != lecturer_id:
        return jsonify({'error': 'Unauthorized. Only the lecturer of this course can create sections.'}), 403
    
    sql = text("""
        INSERT INTO section (section_title, course_id)
        VALUES (:section_title, :course_id)
    """)
    db.session.execute(sql, {
        'section_title': section_title,
        'course_id': course_id
    })
    db.session.commit()
    
    section_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
    
    return jsonify({
        'message': 'Section created successfully',
        'section_id': section_id,
        'section_title': section_title
    })


if __name__ == '__main__':
    app.run(debug=True)