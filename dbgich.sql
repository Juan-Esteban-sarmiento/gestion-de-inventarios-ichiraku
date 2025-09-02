SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

CREATE TABLE `detalle_pedido` (
  `Id_Pedido` int NOT NULL,
  `Id_Producto` int NOT NULL,
  `Fecha_Pedido` date DEFAULT NULL,
  `Cantidad` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `empleados` (
  `Cedula` int NOT NULL,
  `Nombre` varchar(100) NOT NULL,
  `Numero_contacto` int DEFAULT NULL,
  `Contrasena` varchar(100) NOT NULL,
  `Foto` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `informe` (
  `Id_Informe` int NOT NULL,
  `Id_Inf_Pedido` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `inventario` (
  `Id_Inventario` int NOT NULL,
  `Id_Local` int DEFAULT NULL,
  `Id_Producto` int DEFAULT NULL,
  `Cantidad` int NOT NULL,
  `Fecha_caducidad` date DEFAULT NULL,
  `Fecha_ingreso` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `locales` (
  `Id_Local` int NOT NULL,
  `Nombre` varchar(100) NOT NULL,
  `Direccion` varchar(255) DEFAULT NULL,
  `Foto` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `notificaciones` (
  `Id_Notificaciones` int NOT NULL,
  `Id_Inventario` int DEFAULT NULL,
  `Mensaje` varchar(255) DEFAULT NULL,
  `Fecha` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `pedido` (
  `Id_Pedido` int NOT NULL,
  `Id_Inventario` int DEFAULT NULL,
  `Cedula` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

CREATE TABLE `productos` (
  `Id_Producto` int NOT NULL,
  `Nombre` varchar(100) NOT NULL,
  `Categoria` varchar(100) DEFAULT NULL,
  `Unidad` varchar(50) DEFAULT NULL,
  `Foto` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

ALTER TABLE `detalle_pedido`
  ADD PRIMARY KEY (`Id_Pedido`,`Id_Producto`),
  ADD KEY `Id_Producto` (`Id_Producto`);

ALTER TABLE `empleados`
  ADD PRIMARY KEY (`Cedula`);

ALTER TABLE `informe`
  ADD PRIMARY KEY (`Id_Informe`),
  ADD KEY `Id_Inf_Pedido` (`Id_Inf_Pedido`);

ALTER TABLE `inventario`
  ADD PRIMARY KEY (`Id_Inventario`),
  ADD KEY `Id_Local` (`Id_Local`),
  ADD KEY `Id_Producto` (`Id_Producto`);

ALTER TABLE `locales`
  ADD PRIMARY KEY (`Id_Local`);

ALTER TABLE `notificaciones`
  ADD PRIMARY KEY (`Id_Notificaciones`),
  ADD KEY `Id_Inventario` (`Id_Inventario`);

ALTER TABLE `pedido`
  ADD PRIMARY KEY (`Id_Pedido`),
  ADD KEY `Id_Inventario` (`Id_Inventario`),
  ADD KEY `Cedula` (`Cedula`);

ALTER TABLE `productos`
  ADD PRIMARY KEY (`Id_Producto`);

ALTER TABLE `detalle_pedido`
  ADD CONSTRAINT `detalle_pedido_ibfk_1` FOREIGN KEY (`Id_Pedido`) REFERENCES `pedido` (`Id_Pedido`),
  ADD CONSTRAINT `detalle_pedido_ibfk_2` FOREIGN KEY (`Id_Producto`) REFERENCES `productos` (`Id_Producto`);

ALTER TABLE `informe`
  ADD CONSTRAINT `informe_ibfk_1` FOREIGN KEY (`Id_Inf_Pedido`) REFERENCES `pedido` (`Id_Pedido`);

ALTER TABLE `inventario`
  ADD CONSTRAINT `inventario_ibfk_1` FOREIGN KEY (`Id_Local`) REFERENCES `locales` (`Id_Local`),
  ADD CONSTRAINT `inventario_ibfk_2` FOREIGN KEY (`Id_Producto`) REFERENCES `productos` (`Id_Producto`);

ALTER TABLE `notificaciones`
  ADD CONSTRAINT `notificaciones_ibfk_1` FOREIGN KEY (`Id_Inventario`) REFERENCES `inventario` (`Id_Inventario`);

ALTER TABLE `pedido`
  ADD CONSTRAINT `pedido_ibfk_1` FOREIGN KEY (`Id_Inventario`) REFERENCES `inventario` (`Id_Inventario`),
  ADD CONSTRAINT `pedido_ibfk_2` FOREIGN KEY (`Cedula`) REFERENCES `empleados` (`Cedula`);
COMMIT;
