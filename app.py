from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///course_management.db'
db = SQLAlchemy(app)

class User(db.Model):
    userid = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20))

class Student(db.Model):
    stud_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    name = db.Column(db.String(100))

class Lecturer(db.Model):
    lect_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    name = db.Column(db.String(100))

class Admin(db.Model):
    admin_id = db.Column(db.Integer, db.ForeignKey('user.userid'), primary_key=True)
    email = db.Column(db.String(100))

class Course(db.Model):
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(255))
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturer.lect_id'))

class CourseRegistration(db.Model):
    stud_id = db.Column(db.Integer, db.ForeignKey('student.stud_id'), primary_key=True)
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
    stud_id = db.Column(db.Integer, db.ForeignKey('student.stud_id'), primary_key=True)
    grade = db.Column(db.Float)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user = User(userid=data['userid'], password=data['password'], role=data['role'])
    db.session.add(user)
    if data['role'] == 'student':
        db.session.add(Student(stud_id=data['userid'], name=data.get('name', '')))
    elif data['role'] == 'lecturer':
        db.session.add(Lecturer(lect_id=data['userid'], name=data.get('name', '')))
    elif data['role'] == 'admin':
        db.session.add(Admin(admin_id=data['userid'], email=data.get('email', '')))
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(userid=data['userid'], password=data['password']).first()
    if user:
        return jsonify({'message': 'Login successful', 'role': user.role})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/courses', methods=['POST'])
def create_course():
    data = request.json
    user = User.query.get(data['admin_id'])
    if not user or user.role != 'admin':
        return jsonify({'message': 'Only admins can create courses'}), 403
    course = Course(course_name=data['course_name'], lecturer_id=data['lecturer_id'])
    db.session.add(course)
    db.session.commit()
    return jsonify({'message': 'Course created'})

@app.route('/courses', methods=['GET'])
def get_courses():
    return jsonify([{'id': c.course_id, 'name': c.course_name} for c in Course.query.all()])

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
    students = db.session.query(Student).join(CourseRegistration).filter(CourseRegistration.course_id == course_id).all()
    return jsonify([{'id': s.stud_id, 'name': s.name} for s in students])

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

@app.route('/content/<int:course_id>', methods=['GET', 'POST'])
def course_content(course_id):
    if request.method == 'GET':
        return jsonify([{'section': c.section, 'content': c.content} for c in CourseContent.query.filter_by(course_id=course_id)])
    data = request.json
    content = CourseContent(course_id=course_id, section=data['section'], content=data['content'])
    db.session.add(content)
    db.session.commit()
    return jsonify({'message': 'Content added'})

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

@app.route('/report/popular-courses', methods=['GET'])
def top_courses():
    results = db.session.query(Course.course_name, func.count(CourseRegistration.stud_id).label('num_students')) \
        .join(CourseRegistration).group_by(Course.course_id).order_by(func.count(CourseRegistration.stud_id).desc()).limit(10).all()
    return jsonify([{'course': r[0], 'students': r[1]} for r in results])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)