INSERT INTO producto (codigo, nombre, descripcion, categoria, precio_unitario, cantidad, stock_minimo) VALUES
('A001', 'Armazón Clásico', 'Armazón metálico', 'Armazones', 1500, 10, 3),
('A002', 'Lente Antirreflejo', 'Lente con tratamiento', 'Lentes', 2000, 5, 2),
-- (8 más...)

INSERT INTO medico (nombre, apellido, matricula, especialidad, contacto, porcentaje_comision) VALUES
('Ana', 'Gómez', '12345', 'Oftalmología', 'ana@example.com', 10),
('Luis', 'Pérez', '67890', 'Oftalmología', 'luis@example.com', 15),
('María', 'Rodríguez', '54321', 'Oftalmología', 'maria@example.com', 20);

INSERT INTO paciente (nombre, apellido, dni, fecha_nacimiento, obra_social, contacto) VALUES
('Carlos', 'López', '30123456', '1980-05-10', 'OSDE', 'carlos@example.com'),
-- (2 más...)

-- Recetas + ventas asociadas
-- INSERT INTO receta (...) VALUES (...)
-- INSERT INTO venta (...) VALUES (...)