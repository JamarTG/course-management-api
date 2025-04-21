CREATE DATABASE IF NOT EXISTS course_management;
USE course_management;

CREATE TABLE IF NOT EXISTS User (
    userid INT AUTO_INCREMENT PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    role ENUM('student', 'lecturer', 'admin') NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS Course (
    course_id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    lecturer_id INT
);

CREATE TABLE IF NOT EXISTS Course_Registration (
    stud_id INT NOT NULL,
    course_id INT NOT NULL,
    PRIMARY KEY (stud_id, course_id)
);

CREATE TABLE IF NOT EXISTS Assignment (
    assign_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    due_date DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS Submission (
    assign_id INT NOT NULL,
    stud_id INT NOT NULL,
    grade DECIMAL(5,2),
    submission_url VARCHAR(255) NOT NULL,
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (assign_id, stud_id)
);

CREATE TABLE IF NOT EXISTS Calendar_Event (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_title VARCHAR(255) NOT NULL,
    event_date DATETIME NOT NULL,
    course_id INT NOT NULL
);

CREATE TABLE IF NOT EXISTS Section (
    section_id INT AUTO_INCREMENT PRIMARY KEY,
    section_title VARCHAR(50) NOT NULL,
    course_id INT NOT NULL
);

CREATE TABLE IF NOT EXISTS Course_Content (
    content_id INT AUTO_INCREMENT PRIMARY KEY,
    content_title VARCHAR(255) NOT NULL,
    content_url VARCHAR(255) NOT NULL,
    content_type ENUM('link', 'file', 'slide') NOT NULL,
    section_id INT NOT NULL,
    course_id INT NOT NULL
);

CREATE TABLE IF NOT EXISTS Forum (
    forum_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL,
    forum_title VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Discussion_Thread (
    thread_id INT AUTO_INCREMENT PRIMARY KEY,
    dis_title VARCHAR(255) NOT NULL,
    forum_id INT NOT NULL,
    created_by INT NOT NULL
);

CREATE TABLE IF NOT EXISTS Thread_Reply (
    reply_id INT AUTO_INCREMENT PRIMARY KEY,
    thread_id INT NOT NULL,
    user_id INT NOT NULL,
    reply_text TEXT NOT NULL,
    replied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parent_reply_id INT DEFAULT NULL
);


ALTER TABLE Course
ADD FOREIGN KEY (lecturer_id) REFERENCES User(userid);

ALTER TABLE Course_Registration
ADD FOREIGN KEY (stud_id) REFERENCES User(userid),
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id);

ALTER TABLE Assignment
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id);

ALTER TABLE Submission
ADD FOREIGN KEY (assign_id) REFERENCES Assignment(assign_id),
ADD FOREIGN KEY (stud_id) REFERENCES User(userid);

ALTER TABLE Calendar_Event
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id);

ALTER TABLE Course_Content
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id),
ADD FOREIGN KEY (section_id) REFERENCES Section(section_id);

ALTER TABLE Forum
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id);

ALTER TABLE Discussion_Thread
ADD FOREIGN KEY (forum_id) REFERENCES Forum(forum_id),
ADD FOREIGN KEY (created_by) REFERENCES User(userid);

ALTER TABLE Thread_Reply
ADD FOREIGN KEY (thread_id) REFERENCES Discussion_Thread(thread_id),
ADD FOREIGN KEY (user_id) REFERENCES User(userid);

ALTER TABLE Thread_Reply
ADD FOREIGN KEY (parent_reply_id) REFERENCES Thread_Reply(reply_id);

ALTER TABLE Section 
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id);


CREATE OR REPLACE VIEW Courses_With_50_Or_More_Students AS
SELECT 
    c.course_id,
    c.course_name,
    COUNT(cr.stud_id) AS student_count
FROM Course c
JOIN Course_Registration cr ON c.course_id = cr.course_id
GROUP BY c.course_id, c.course_name
HAVING COUNT(cr.stud_id) >= 50;



CREATE OR REPLACE VIEW Students_With_5_Or_More_Courses AS
SELECT 
    u.userid,
    u.name,
    COUNT(cr.course_id) AS course_count
FROM User u
JOIN Course_Registration cr ON u.userid = cr.stud_id
WHERE u.role = 'student'
GROUP BY u.userid, u.name
HAVING COUNT(cr.course_id) >= 5;


CREATE OR REPLACE VIEW Lecturers_With_3_Or_More_Courses AS
SELECT 
    u.userid,
    u.name,
    COUNT(c.course_id) AS course_count
FROM User u
JOIN Course c ON u.userid = c.lecturer_id
WHERE u.role = 'lecturer'
GROUP BY u.userid, u.name
HAVING COUNT(c.course_id) >= 3;


CREATE OR REPLACE VIEW Top_10_Most_Enrolled_Courses AS
SELECT 
    c.course_id,
    c.course_name,
    COUNT(cr.stud_id) AS student_count
FROM Course c
JOIN Course_Registration cr ON c.course_id = cr.course_id
GROUP BY c.course_id, c.course_name
ORDER BY student_count DESC
LIMIT 10;


CREATE OR REPLACE VIEW Top_10_Students_By_Grade AS
SELECT 
    u.userid,
    u.name,
    ROUND(AVG(s.grade), 2) AS average_grade
FROM User u
JOIN Submission s ON u.userid = s.stud_id
WHERE u.role = 'student'
GROUP BY u.userid, u.name
HAVING COUNT(s.grade) > 0
ORDER BY average_grade DESC
LIMIT 10;
