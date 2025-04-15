from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_
from dotenv import load_dotenv
import os


load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')


db = SQLAlchemy(app)

# ---------------------- Models ---------------------- #
class User(db.Model):
    userid = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)

class Course(db.Model):
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(255))
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.userid'))

class CourseRegistration(db.Model):
    stud_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'), primary_key=True)

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))
    title = db.Column(db.String(100))
    date = db.Column(db.String(50))

class Forum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))
    title = db.Column(db.String(100))

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forum.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('thread.id'), nullable=True)
    title = db.Column(db.String(255))
    body = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.userid'))

class CourseContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))
    section = db.Column(db.String(100))
    content = db.Column(db.Text)

class Assignment(db.Model):
    assign_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'))

class Submission(db.Model):
    assign_id = db.Column(db.Integer, db.ForeignKey('assignment.assign_id'), primary_key=True)
    stud_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    grade = db.Column(db.Float)

# Notes to self
# Ensure password is properly hashed
# 

# ---------------------- Auth ---------------------- #
# ✅
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user = User(userid=data['userid'], password=data['password'], role=data['role'], 
                name=data.get('name', ''), email=data.get('email', ''))
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'userid': user.userid,
            'name': user.name,
            'role': user.role,
            'email': user.email
        }
    })
    
#     {
#     "message": "User registered successfully",
#     "user": {
#         "email": "alice@gmail.com",
#         "name": "Alice Johnson",
#         "role": "student",
#         "userid": 1002
#     }
# }


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email'], password=data['password']).first()

    if user:
        return jsonify({'message': 'Login successful', 'role': user.role})
    return jsonify({'message': 'Invalid credentials'}), 401

# {
#   "email":"alice@gmail.com",
#   "password":"securePass123"
# }

# ---------------------- Course Management ---------------------- #
@app.route('/courses', methods=['POST'])
def create_course():
    data = request.json

    # Check if required fields are in the request
    required_fields = ['userid', 'course_name', 'lecturer_id']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({'message': f'Missing fields: {", ".join(missing_fields)}'}), 400

   
    user = User.query.get(data['userid'])
    if not user or user.role != 'admin':  
        return jsonify({'message': 'Only admins can create courses'}), 403


    course = Course(course_name=data['course_name'], lecturer_id=data['lecturer_id'])
    db.session.add(course)
    db.session.commit()

    return jsonify({'message': 'Course created', 'course_id': course.course_id})

@app.route('/courses', methods=['GET'])
def get_courses():
    return jsonify([{'course_id': c.course_id, 'course_name': c.course_name} for c in Course.query.all()])

@app.route('/courses/student/<int:stud_id>', methods=['GET'])
def student_courses(stud_id):
    courses = db.session.query(Course).join(CourseRegistration).filter(CourseRegistration.stud_id == stud_id).all()
    return jsonify([{'id': c.course_id, 'name': c.course_name} for c in courses])

@app.route('/courses/lecturer/<int:lect_id>', methods=['GET'])
def lecturer_courses(lect_id):
    return jsonify([{'id': c.course_id, 'name': c.course_name} for c in Course.query.filter_by(lecturer_id=lect_id)])

@app.route('/register-course', methods=['POST'])
def register_course():
    data = request.json
    reg = CourseRegistration(stud_id=data['stud_id'], course_id=data['course_id'])
    db.session.add(reg)
    db.session.commit()
    return jsonify({'message': 'Student registered for course'})

@app.route('/course-members/<int:course_id>', methods=['GET'])
def get_course_members(course_id):
    users = db.session.query(User).join(CourseRegistration).filter(
        CourseRegistration.course_id == course_id,
        User.userid == CourseRegistration.stud_id,
        User.role == 'student'
    ).all()
    return jsonify([{'id': u.userid, 'name': u.name} for u in users])

# ---------------------- Calendar ---------------------- #
@app.route('/calendar/<int:course_id>', methods=['GET'])
def get_course_events(course_id):
    return jsonify([{'title': e.title, 'date': e.date} for e in CalendarEvent.query.filter_by(course_id=course_id)])

@app.route('/calendar/student/<int:stud_id>/<string:date>', methods=['GET'])
def get_student_events_by_date(stud_id, date):
    course_ids = db.session.query(CourseRegistration.course_id).filter_by(stud_id=stud_id).all()
    course_ids = [id for (id,) in course_ids]
    events = CalendarEvent.query.filter(and_(CalendarEvent.course_id.in_(course_ids), CalendarEvent.date == date)).all()
    return jsonify([{'title': e.title, 'date': e.date} for e in events])

@app.route('/calendar', methods=['POST'])
def create_event():
    data = request.json
    event = CalendarEvent(course_id=data['course_id'], title=data['title'], date=data['date'])
    db.session.add(event)
    db.session.commit()
    return jsonify({'message': 'Event created'})

# ---------------------- Forums ---------------------- #
@app.route('/forum/<int:course_id>', methods=['GET', 'POST'])
def forum(course_id):
    if request.method == 'GET':
        return jsonify([{'id': f.id, 'title': f.title} for f in Forum.query.filter_by(course_id=course_id)])
    data = request.json
    forum = Forum(course_id=course_id, title=data['title'])
    db.session.add(forum)
    db.session.commit()
    return jsonify({'message': 'Forum created'})

@app.route('/threads/<int:forum_id>', methods=['GET', 'POST'])
def threads(forum_id):
    if request.method == 'GET':
        return jsonify([{'id': t.id, 'title': t.title, 'body': t.body, 'parent': t.parent_id} for t in Thread.query.filter_by(forum_id=forum_id)])
    data = request.json
    thread = Thread(forum_id=forum_id, parent_id=data.get('parent_id'), title=data.get('title', ''), body=data['body'], user_id=data['user_id'])
    db.session.add(thread)
    db.session.commit()
    return jsonify({'message': 'Thread added'})

# ---------------------- Course Content ---------------------- #
@app.route('/content/<int:course_id>', methods=['GET', 'POST'])
def course_content(course_id):
    if request.method == 'GET':
        return jsonify([{'section': c.section, 'content': c.content} for c in CourseContent.query.filter_by(course_id=course_id)])
    data = request.json
    content = CourseContent(course_id=course_id, section=data['section'], content=data['content'])
    db.session.add(content)
    db.session.commit()
    return jsonify({'message': 'Content added'})

# ---------------------- Assignments ---------------------- #
@app.route('/assignment/<int:course_id>', methods=['POST'])
def create_assignment(course_id):
    assignment = Assignment(course_id=course_id)
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'message': 'Assignment created', 'assign_id': assignment.assign_id})

@app.route('/submit', methods=['POST'])
def submit_assignment():
    data = request.json
    submission = Submission(assign_id=data['assign_id'], stud_id=data['stud_id'], grade=data['grade'])
    db.session.add(submission)
    db.session.commit()
    return jsonify({'message': 'Assignment submitted'})

# ---------------------- Reports ---------------------- #
@app.route('/report/popular-courses', methods=['GET'])
def top_courses():
    results = db.session.query(Course.course_name, func.count(CourseRegistration.stud_id).label('num_students')) \
        .join(CourseRegistration).group_by(Course.course_id).order_by(func.count(CourseRegistration.stud_id).desc()).limit(10).all()
    return jsonify([{'course': r[0], 'students': r[1]} for r in results])

# ---------------------- Init ---------------------- #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
