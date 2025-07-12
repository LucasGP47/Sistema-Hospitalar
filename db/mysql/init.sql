CREATE DATABASE IF NOT EXISTS hospital_db;
USE hospital_db;

CREATE TABLE doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    age INT,
    gender VARCHAR(10),
    phone VARCHAR(15),
    address VARCHAR(255),
    doctor_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);

INSERT INTO doctors (name, specialty, phone) VALUES 
('Dr. Carlos Oliveira', 'Cardiologia', '(11) 9999-1111'),
('Dra. Ana Ferreira', 'Neurologia', '(11) 9999-2222'),
('Dr. Paulo Santos', 'Clnico Geral', '(11) 9999-3333');

INSERT INTO patients (name, age, gender, phone, address, doctor_id) VALUES 
('Maria Silva', 45, 'Feminino', '(11) 8888-1111', 'Av. Paulista, 1000', 1),
('João Santos', 32, 'Masculino', '(11) 8888-2222', 'Rua Augusta, 500', 1),
('Ana Costa', 28, 'Feminino', '(11) 8888-3333', 'Rua Oscar Freire, 200', 2),
('Pedro Lima', 55, 'Masculino', '(11) 8888-4444', 'Av. Faria Lima, 800', 3),
('Julia Ramos', 38, 'Feminino', '(11) 8888-5555', 'Rua Consolação, 300', 2);