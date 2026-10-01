-- =====================================================================
-- Impuesto a las Actividades Economicas - Base de datos completa
-- MariaDB (XAMPP, puerto 3306). Pegar completo en la consola mysql.
-- Sin acentos a proposito: evita caracteres danados al pegar en cmd.
-- ATENCION: borra y recrea la base 'impuesto_actividades'.
-- =====================================================================
SET NAMES utf8mb4;
DROP DATABASE IF EXISTS impuesto_actividades;
CREATE DATABASE impuesto_actividades CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE impuesto_actividades;

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL UNIQUE,
  rol ENUM('operador','autorizador') NOT NULL DEFAULT 'operador'
) ENGINE=InnoDB;

CREATE TABLE clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(20) NOT NULL UNIQUE,
  nombre VARCHAR(120) NOT NULL,
  tipo ENUM('empresa','persona') NOT NULL
) ENGINE=InnoDB;

CREATE TABLE productos (
  codigo INT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  actividad ENUM('comercio','industria') NOT NULL,
  precio_general DECIMAL(18,6) NOT NULL DEFAULT 0   -- informativo: NUNCA se usa como respaldo (RF13)
) ENGINE=InnoDB;

-- Cada tarifa pertenece a un producto y tiene fecha de vigencia (version tarifaria)
CREATE TABLE tarifas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  producto_codigo INT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  desde DECIMAL(18,2) NOT NULL,
  hasta DECIMAL(18,2) NOT NULL,
  precio_base DECIMAL(18,6) NOT NULL DEFAULT 0,
  adicional DECIMAL(18,6) NOT NULL DEFAULT 0,
  porcentaje DECIMAL(9,6) NOT NULL DEFAULT 0,
  vigente_desde DATE NOT NULL,
  vigente_hasta DATE NULL,
  activa TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_tar_prod FOREIGN KEY (producto_codigo) REFERENCES productos(codigo),
  CONSTRAINT ck_tar_rango CHECK (desde <= hasta),
  INDEX ix_tar_busqueda (producto_codigo, activa, desde, hasta)
) ENGINE=InnoDB;

-- Periodo anual: guarda precio historico + copia (snapshot) de la tarifa y formula usadas
CREATE TABLE periodos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cliente_id INT NOT NULL,
  producto_codigo INT NOT NULL,
  desde DATE NOT NULL,                       -- incluida
  hasta DATE NOT NULL,                       -- no incluida  [desde, hasta)
  balance DECIMAL(18,2) NOT NULL,
  cantidad DECIMAL(10,2) NOT NULL DEFAULT 1.00,
  precio DECIMAL(18,6) NOT NULL,             -- impuesto mensual calculado
  subtotal DECIMAL(18,2) NOT NULL,           -- cantidad x precio
  tarifa_id INT NULL,
  tarifa_version INT NULL,
  tarifa_desde DECIMAL(18,2) NULL,
  tarifa_hasta DECIMAL(18,2) NULL,
  precio_base DECIMAL(18,6) NULL,
  adicional DECIMAL(18,6) NULL,
  porcentaje DECIMAL(9,6) NULL,
  formula VARCHAR(30) NOT NULL,              -- BLOQUES_CEIL_V2 | PROPORCIONAL_V1
  fecha_calculo DATETIME NOT NULL,
  facturado TINYINT(1) NOT NULL DEFAULT 0,
  creado_por VARCHAR(60) NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  modificado_por VARCHAR(60) NULL,
  modificado_en DATETIME NULL,
  CONSTRAINT fk_per_cli FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  CONSTRAINT fk_per_prod FOREIGN KEY (producto_codigo) REFERENCES productos(codigo),
  CONSTRAINT fk_per_tar FOREIGN KEY (tarifa_id) REFERENCES tarifas(id),
  CONSTRAINT ck_per_fechas CHECK (desde < hasta),
  CONSTRAINT ck_per_balance CHECK (balance > 0),
  INDEX ix_per (cliente_id, producto_codigo, desde, hasta)
) ENGINE=InnoDB;

CREATE TABLE recibos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cliente_id INT NOT NULL,
  producto_codigo INT NOT NULL,
  desde DATE NOT NULL,
  hasta DATE NOT NULL,
  total DECIMAL(18,2) NOT NULL,
  creado_por VARCHAR(60) NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  FOREIGN KEY (producto_codigo) REFERENCES productos(codigo)
) ENGINE=InnoDB;

CREATE TABLE recibo_detalle (
  id INT AUTO_INCREMENT PRIMARY KEY,
  recibo_id INT NOT NULL,
  periodo_id INT NOT NULL,
  desde DATE NOT NULL,
  hasta DATE NOT NULL,
  meses DECIMAL(10,4) NOT NULL,
  cantidad DECIMAL(10,2) NOT NULL,
  precio DECIMAL(18,6) NOT NULL,
  importe DECIMAL(18,2) NOT NULL,     -- cantidad x precio mensual x meses aplicables
  FOREIGN KEY (recibo_id) REFERENCES recibos(id),
  FOREIGN KEY (periodo_id) REFERENCES periodos(id)
) ENGINE=InnoDB;

CREATE TABLE bitacora (
  id INT AUTO_INCREMENT PRIMARY KEY,
  periodo_id INT NULL,
  usuario VARCHAR(60) NOT NULL,
  accion VARCHAR(30) NOT NULL,
  detalle TEXT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_bit (periodo_id)
) ENGINE=InnoDB;

-- ------------------------- Datos iniciales -------------------------
INSERT INTO usuarios (nombre, rol) VALUES ('operador1','operador'), ('autorizador1','autorizador');

INSERT INTO clientes (codigo, nombre, tipo) VALUES
 ('EMP-001','Distribuidora El Progreso S.A. de C.V.','empresa'),
 ('EMP-002','Industrias Cuscatlan S.A.','empresa'),
 ('PER-001','Juan Perez (persona natural)','persona');

INSERT INTO productos (codigo, nombre, actividad, precio_general) VALUES
 (11801,'Impuesto a las Actividades Economicas - Comercio','comercio',0),
 (11802,'Impuesto a las Actividades Economicas - Industria','industria',0);

-- Tabla tarifaria del documento (producto 11801). Se omite a proposito el rango 6,000.01 - 8,000.00
-- (pendiente de aprobacion, seccion 18.2): el sistema lo rechaza hasta que se configure.
INSERT INTO tarifas (producto_codigo, version, desde, hasta, precio_base, adicional, porcentaje, vigente_desde) VALUES
 (11801,1,        0.01,       500.00,   1.50, 0.00,0,'2020-01-01'),
 (11801,1,      500.01,     1000.00,   1.50, 3.00,0,'2020-01-01'),
 (11801,1,     1000.01,     2000.00,   3.00, 3.00,0,'2020-01-01'),
 (11801,1,     2000.01,     3000.00,   6.00, 3.00,0,'2020-01-01'),
 (11801,1,     3000.01,     6000.00,   9.00, 2.00,0,'2020-01-01'),
 (11801,1,     8000.01,    18000.00,  15.00, 2.00,0,'2020-01-01'),
 (11801,1,    18000.01,    30000.00,  39.00, 2.00,0,'2020-01-01'),
 (11801,1,    30000.01,    60000.00,  63.00, 1.00,0,'2020-01-01'),
 (11801,1,    60000.01,   100000.00,  93.00, 0.80,0,'2020-01-01'),
 (11801,1,   100000.01,   200000.00, 125.00, 0.70,0,'2020-01-01'),
 (11801,1,   200000.01,   300000.00, 195.00, 0.60,0,'2020-01-01'),
 (11801,1,   300000.01,   400000.00, 255.00, 0.45,0,'2020-01-01'),
 (11801,1,   400000.01,   500000.00, 300.00, 0.40,0,'2020-01-01'),
 (11801,1,   500000.01,  1000000.00, 340.00, 0.30,0,'2020-01-01'),
 (11801,1,  1000000.01, 99999999.99, 490.00, 0.18,0,'2020-01-01');

-- Suposicion de trabajo (seccion 18.1): Industria usa la misma tabla, pero como filas propias
-- (configuracion explicita por producto; nunca se intercambian en el calculo).
INSERT INTO tarifas (producto_codigo, version, desde, hasta, precio_base, adicional, porcentaje, vigente_desde)
SELECT 11802, version, desde, hasta, precio_base, adicional, porcentaje, vigente_desde
FROM tarifas WHERE producto_codigo = 11801;

-- Periodos historicos de la seccion 7 (cliente EMP-001, comercio 11801). Suma visual = 20.10
INSERT INTO periodos (cliente_id, producto_codigo, desde, hasta, balance, cantidad, precio, subtotal, tarifa_id, tarifa_version,
                      tarifa_desde, tarifa_hasta, precio_base, adicional, porcentaje, formula, fecha_calculo, facturado, creado_por)
SELECT 1, 11801, x.d, x.h, x.b, 1.00, x.p, x.p, t.id, 1, t.desde, t.hasta, t.precio_base, t.adicional, 0, x.f, NOW(), x.fac, 'carga_inicial'
FROM (
  SELECT '2022-01-01' d, '2023-01-01' h, 700.00 b, 2.10 p, 'PROPORCIONAL_V1' f, 1 fac UNION ALL
  SELECT '2023-01-01','2024-01-01',545.00,4.50,'BLOQUES_CEIL_V2',1 UNION ALL
  SELECT '2024-01-01','2025-01-01',550.00,4.50,'BLOQUES_CEIL_V2',1 UNION ALL
  SELECT '2025-01-01','2026-01-01',550.00,4.50,'BLOQUES_CEIL_V2',1 UNION ALL
  SELECT '2026-01-01','2027-01-01',550.00,4.50,'BLOQUES_CEIL_V2',0
) x
JOIN tarifas t ON t.producto_codigo = 11801 AND t.desde <= x.b AND x.b <= t.hasta;

INSERT INTO bitacora (periodo_id, usuario, accion, detalle)
SELECT id, 'carga_inicial', 'CREACION', CONCAT('Periodo historico ', desde, ' a ', hasta) FROM periodos;

-- Verificacion rapida (debe mostrar 5 filas, suma 20.10)
SELECT desde, hasta, balance, producto_codigo, ROUND(precio,2) precio, formula FROM periodos ORDER BY desde;
SELECT SUM(precio) AS total_referencial FROM periodos;
