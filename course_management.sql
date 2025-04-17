-- Make the properties not null

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
    course_name VARCHAR(255),
    lecturer_id INT
);

CREATE TABLE IF NOT EXISTS Course_Registration (
    stud_id INT,
    course_id INT,
    PRIMARY KEY (stud_id, course_id)
);

CREATE TABLE IF NOT EXISTS Assignment (
    assign_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT,
    title VARCHAR(100),
    description TEXT,
    due_date DATETIME
);

CREATE TABLE IF NOT EXISTS Submission (
    assign_id INT,
    stud_id INT,
    grade DECIMAL(5,2),
    submission_url VARCHAR(255),
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (assign_id, stud_id)
);


CREATE TABLE IF NOT EXISTS Calendar_Event (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_title VARCHAR(255),
    event_date DATETIME,
    course_id INT
);


CREATE TABLE IF NOT EXISTS Section (
    section_id INT AUTO_INCREMENT PRIMARY KEY,
    section_title VARCHAR(50) NOT NULL, 
    course_id INT,  
   
);

CREATE TABLE IF NOT EXISTS Course_Content (
    content_id INT AUTO_INCREMENT PRIMARY KEY,
    content_title VARCHAR(255),
    content_url VARCHAR(255), 
    content_type ENUM('link', 'file', 'slide') NOT NULL,
    section_id INT,
    course_id INT
);



CREATE TABLE IF NOT EXISTS Forum (
    forum_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT
    forum_title VARCHAR(255) NOT NULL  
);

CREATE TABLE IF NOT EXISTS Discussion_Thread (
    thread_id INT AUTO_INCREMENT PRIMARY KEY,
    dis_title VARCHAR(255),
    forum_id INT,
    created_by INT
);

CREATE TABLE IF NOT EXISTS Thread_Reply (
    reply_id INT AUTO_INCREMENT PRIMARY KEY,
    thread_id INT,
    user_id INT,
    reply_text TEXT,
    replied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id);
add FOREIGN KEY (section_id) REFERENCES Section(section_id)

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
ADD FOREIGN KEY (course_id) REFERENCES Course(course_id)