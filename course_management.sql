-- ALTER TABLE user ADD COLUMN name TEXT;
-- ALTER TABLE user ADD COLUMN email TEXT;

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
    course_id INT
);

CREATE TABLE IF NOT EXISTS Submission (
    assign_id INT,
    stud_id INT,
    grade DECIMAL(5,2),
    PRIMARY KEY (assign_id, stud_id)
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
