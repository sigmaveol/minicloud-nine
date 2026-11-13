CREATE DATABASE IF NOT EXISTS studentdb;
USE studentdb;

CREATE TABLE IF NOT EXISTS students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(10) NOT NULL,
    fullname VARCHAR(100) NOT NULL,
    dob DATE,
    major VARCHAR(50)
);

INSERT INTO students (student_id, fullname, dob, major) VALUES 
('SV001', 'Nguyen Van A', '2002-03-15', 'Computer Science'),
('SV002', 'Tran Thi B', '2001-11-02', 'Data Science'),
('SV003', 'Le Van C', '2002-07-20', 'Cybersecurity');

