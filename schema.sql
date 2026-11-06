CREATE DATABASE IF NOT EXISTS bioalert CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bioalert;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL UNIQUE,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS consultas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  departamento VARCHAR(80) NOT NULL,
  municipio VARCHAR(80) NOT NULL,
  cultivo VARCHAR(40) NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Datos del IDEAM ya agregados por día y por estación
CREATE TABLE IF NOT EXISTS clima_diario (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  departamento VARCHAR(80) NOT NULL,
  municipio VARCHAR(80) NOT NULL,
  estacion_codigo VARCHAR(20) NOT NULL,
  estacion_nombre VARCHAR(120),
  fecha DATE NOT NULL,
  variable ENUM('precipitacion','temperatura','humedad') NOT NULL,
  valor_medio DOUBLE, valor_min DOUBLE, valor_max DOUBLE, valor_suma DOUBLE,
  n_obs INT,
  UNIQUE KEY uq_obs (estacion_codigo, fecha, variable),
  INDEX idx_lugar (departamento, municipio, fecha)
);

-- Resultado del modelo matemático (grados-día, HR media, precipitación acumulada)
CREATE TABLE IF NOT EXISTS resultados_modelo (
  id INT AUTO_INCREMENT PRIMARY KEY,
  consulta_id INT NOT NULL,
  fecha_desde DATE, fecha_hasta DATE, n_dias INT,
  t_media DOUBLE, gda DOUBLE, hr_media DOUBLE, p_acum DOUBLE,
  riesgo VARCHAR(10),
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (consulta_id) REFERENCES consultas(id)
);

-- Conocimiento sobre plagas (sale de CropLife LA)
CREATE TABLE IF NOT EXISTS plagas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre_comun VARCHAR(80), nombre_cientifico VARCHAR(80) UNIQUE, cultivo VARCHAR(40)
);
CREATE TABLE IF NOT EXISTS conocimiento_plaga (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plaga_id INT NOT NULL,
  seccion VARCHAR(255),
  contenido TEXT NOT NULL,
  fuente_url VARCHAR(255),
  FOREIGN KEY (plaga_id) REFERENCES plagas(id)
);

CREATE TABLE IF NOT EXISTS preguntas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT,
  pregunta TEXT NOT NULL,
  respuesta TEXT,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
