CREATE DATABASE IF NOT EXISTS studentdb;
USE studentdb;

CREATE TABLE IF NOT EXISTS students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(10) NOT NULL,
    fullname VARCHAR(100) NOT NULL,
    dob DATE,
    major VARCHAR(50),
    gpa DECIMAL(3, 2)
);

INSERT INTO students (student_id, fullname, dob, major, gpa) VALUES 
('SV001', 'Nguyễn Hoàng Nam', '2002-03-15', 'Computer Science', 3.45),
('SV002', 'Trần Thị Mai Phương', '2001-11-02', 'Information Systems', 3.72),
('SV003', 'Lê Minh Tuấn', '2002-07-20', 'Software Engineering', 3.15),
('SV004', 'Phạm Thu Hà', '2003-05-10', 'Data Science', 3.88),
('SV005', 'Hoàng Đức Anh', '2002-12-01', 'Cybersecurity', 3.50);