from faker import Faker
from random import randint, sample
from collections import defaultdict

NUM_ADMINS = 3
NUM_LECTURERS = 40
NUM_STUDENTS = 400 # will be changed to 10,000 later
NUM_COURSES = 200
MIN_COURSES_PER_STUDENT = 3
MAX_COURSES_PER_STUDENT = 6
MIN_STUDENTS_PER_COURSE = 10
MAX_COURSES_PER_LECTURER = 5

if __name__ == "__main__":
    fake = Faker()
    user_id = 1
    courses = []
    course_registrations = defaultdict(set)
    student_ids = []
    lecturer_ids = []
    
    with open("database_population.sql", "w") as f:

        # Insert Admins
        for _ in range(NUM_ADMINS):
            f.write(f"INSERT INTO User(userid, password, role, name, email) VALUES ({user_id}, '{fake.password()}', 'admin', '{fake.name()}', '{fake.email()}');\n")
            user_id += 1

        # Insert Lecturers
        for _ in range(NUM_LECTURERS):
            f.write(f"INSERT INTO User(userid, password, role, name, email) VALUES ({user_id}, '{fake.password()}', 'lecturer', '{fake.name()}', '{fake.email()}');\n")
            lecturer_ids.append(user_id)
            user_id += 1

        # Insert Students
        for _ in range(NUM_STUDENTS):
            f.write(f"INSERT INTO User(userid, password, role, name, email) VALUES ({user_id}, '{fake.password()}', 'student', '{fake.name()}', '{fake.email()}');\n")
            student_ids.append(user_id)
            user_id += 1

        f.write("\n-- COURSES\n")
      
        course_id = 1
        lecturer_course_count = defaultdict(int)
        for _ in range(NUM_COURSES):
            while True:
                lecturer = lecturer_ids[randint(0, NUM_LECTURERS - 1)]
                if lecturer_course_count[lecturer] < MAX_COURSES_PER_LECTURER:
                    lecturer_course_count[lecturer] += 1
                    break
            course_name = f"{fake.word().title()} {fake.word().title()}"
            f.write(f"INSERT INTO Course(course_id, course_name, lecturer_id) VALUES ({course_id}, '{course_name}', {lecturer});\n")
            courses.append(course_id)
            course_id += 1

        f.write("\n-- COURSE REGISTRATIONS\n")

    
        for course_id in courses:
            selected_students = sample(student_ids, MIN_STUDENTS_PER_COURSE)
            for sid in selected_students:
                course_registrations[sid].add(course_id)
                f.write(f"INSERT INTO Course_Registration(stud_id, course_id) VALUES ({sid}, {course_id});\n")

        # Now complete student enrollments to have 3-6 courses
        for sid in student_ids:
            current = len(course_registrations[sid])
            target = randint(MIN_COURSES_PER_STUDENT, MAX_COURSES_PER_STUDENT)
            if current >= target:
                continue
            available_courses = list(set(courses) - course_registrations[sid])
            additional_courses = sample(available_courses, target - current)
            for cid in additional_courses:
                course_registrations[sid].add(cid)
                f.write(f"INSERT INTO Course_Registration(stud_id, course_id) VALUES ({sid}, {cid});\n")

        # Append the section and assignment for course_id = 1
        f.write("\n-- SECTION FOR COURSE 1\n")
        f.write("INSERT INTO Section (section_id, section_title, course_id) VALUES (1, 'Week 1 - Introduction', 1);\n")
        
        f.write("\n-- ASSIGNMENT FOR COURSE 1\n")
        f.write("INSERT INTO Assignment (course_id, title, description, due_date) VALUES (1, 'Midterm Project', 'Build a web app', '2025-05-01 23:59:00');\n")

        print("file generated successfully")
