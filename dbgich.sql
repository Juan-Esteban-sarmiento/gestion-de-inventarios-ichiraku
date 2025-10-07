
-- Base de datos: dbgich
-- Compatible con PostgreSQL

-- =========================================
-- TABLA: roles
-- =========================================
CREATE TABLE roles (
  Id_Rol SERIAL PRIMARY KEY,
  Nombre VARCHAR(100) NOT NULL
);

-- =========================================
-- TABLA: locales
-- =========================================
CREATE TABLE locales (
  Id_Local SERIAL PRIMARY KEY,
  Nombre VARCHAR(100) NOT NULL,
  Direccion TEXT,
  Foto TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- =========================================
-- TABLA: empleados
-- =========================================
CREATE TABLE empleados (
  Cedula SERIAL PRIMARY KEY,
  Nombre VARCHAR(100) NOT NULL,
  Numero_contacto INT,
  Contrasena VARCHAR(100) NOT NULL,
  Foto BYTEA,
  Id_Rol INT REFERENCES roles(Id_Rol),
  User_ID UUID DEFAULT gen_random_uuid(),
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- =========================================
-- TABLA: productos
-- =========================================

CREATE TABLE productos (
  Id_Producto SERIAL PRIMARY KEY,
  Nombre VARCHAR(100) NOT NULL,
  Categoria VARCHAR(100),
  Unidad VARCHAR(50),
  Foto TEXT,
  Precio_Compra NUMERIC(10,2),             -- nuevo: costo unitario
  Precio_Venta NUMERIC(10,2),              -- nuevo: precio al público
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- =========================================
-- TABLA: inventario
-- =========================================
CREATE TABLE inventario (
  Id_Inventario SERIAL PRIMARY KEY,
  Id_Local INT REFERENCES locales(Id_Local),
  Id_Producto INT REFERENCES productos(Id_Producto),
  Cantidad INT NOT NULL,
  Fecha_caducidad DATE,
  Fecha_ingreso DATE,
  Stock_Minimo INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- =========================================
-- TABLA: pedido
-- =========================================

CREATE TABLE pedido (
  Id_Pedido SERIAL PRIMARY KEY,
  Id_Inventario INT REFERENCES inventario(Id_Inventario),
  Cedula INT REFERENCES empleados(Cedula),
  Fecha_Pedido TIMESTAMP DEFAULT now(),
  Estado VARCHAR(50) DEFAULT 'Pendiente'
);

-- =========================================
-- TABLA: detalle_pedido
-- =========================================
CREATE TABLE detalle_pedido (
  Id_Pedido INT REFERENCES pedido(Id_Pedido),
  Id_Producto INT REFERENCES productos(Id_Producto),
  Fecha_Pedido DATE,
  Cantidad INT NOT NULL,
  Precio NUMERIC(10,2),
  Subtotal NUMERIC(10,2) GENERATED ALWAYS AS (Cantidad * Precio) STORED,
  PRIMARY KEY (Id_Pedido, Id_Producto)
);

-- =========================================
-- TABLA: informe
-- =========================================
CREATE TABLE informe (
  Id_Informe SERIAL PRIMARY KEY,
  Id_Inf_Pedido INT REFERENCES pedido(Id_Pedido),
  Fecha_Creacion TIMESTAMP DEFAULT now()
);

-- =========================================
-- TABLA: notificaciones
-- =========================================
CREATE TABLE notificaciones (
  Id_Notificaciones SERIAL PRIMARY KEY,
  Id_Inventario INT REFERENCES inventario(Id_Inventario),
  Mensaje TEXT,
  Tipo VARCHAR(50),
  Leido BOOLEAN DEFAULT FALSE,
  Fecha TIMESTAMP DEFAULT now()
);

-- =========================================
-- TABLA: movimiento_inventario
-- =========================================
CREATE TABLE movimiento_inventario (
  Id_Movimiento SERIAL PRIMARY KEY,
  Id_Producto INT REFERENCES productos(Id_Producto)
);

-- =========================================
-- TABLA: administrador
-- =========================================
CREATE TABLE administrador (
  ID SERIAL PRIMARY KEY,
  Nombre VARCHAR(100) NOT NULL,
  Contrasena VARCHAR(40) NOT NULL,
  Foto BYTEA
);


INSERT INTO administrador (ID, Nombre, Contrasena, Foto) VALUES
(1, 'juan', 'Admin123', decode('FFD8FFE000104A46494600010100000100010000...', 'hex'));

INSERT INTO pedido (Id_Pedido, Id_Inventario, Cedula, Fecha_Pedido, Estado) VALUES
(1, 21, 8, '2025-10-01 10:00:00', 'Pendiente'),
(2, 23, 1000225584, '2025-10-01 11:00:00', 'Pendiente'),
(3, 26, 8, '2025-10-01 12:00:00', 'Pendiente');

INSERT INTO detalle_pedido (Id_Pedido, Id_Producto, Fecha_Pedido, Cantidad) VALUES
(1, 3, '2025-10-01', 2),
(1, 234567, '2025-10-01', 1),
(2, 2, '2025-10-01', 3),
(2, 3, '2025-10-01', 5),
(2, 234567, '2025-10-01', 4),
(3, 1, '2025-10-01', 2),
(3, 54321, '2025-10-01', 6);

INSERT INTO empleados (Cedula, Nombre, Numero_contacto, Contrasena, Foto)
VALUES
(8, 'Fuad', 2147483647, '1234567', decode('FFD8FFE000104A46494600010101006000600000...', 'hex')),
(1000225584, 'juan', 456789, '123', decode('FFD8FFE000104A46494600010100000100010000...', 'hex'));



INSERT INTO informe (Id_Informe, Id_Inf_Pedido, Fecha_Creacion)
VALUES
(1, 1, now()),
(2, 1, now());


INSERT INTO locales (Id_Local, Nombre, Direccion)
VALUES
(1, 'ichiraku ramen 1', 'calle 70 noroeste');


INSERT INTO inventario (Id_Inventario, Id_Local, Id_Producto, Cantidad, Fecha_caducidad, Fecha_ingreso)
VALUES
(21, 1, 3, 2, '2025-11-01', '2025-10-01'),
(22, 1, 234567, 1, '2025-11-01', '2025-10-01'),
(23, 1, 2, 3, '2025-11-01', '2025-10-01'),
(24, 1, 234567, 4, '2025-11-01', '2025-10-01'),
(25, 1, 3, 5, '2025-11-01', '2025-10-01'),
(26, 1, 1, 2, '2025-11-01', '2025-10-01'),
(27, 1, 54321, 6, '2025-11-01', '2025-10-01');

