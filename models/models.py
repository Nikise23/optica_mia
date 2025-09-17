from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(200))
    categoria = db.Column(db.String(50))
    precio_unitario = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    stock_minimo = db.Column(db.Integer, nullable=False)

class Paciente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    dni = db.Column(db.String(20))
    fecha_nacimiento = db.Column(db.Date)
    obra_social = db.Column(db.String(100))
    contacto = db.Column(db.String(100))
    # Relación para acceder desde Receta como r.paciente
    recetas = db.relationship('Receta', backref='paciente')

class Medico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    matricula = db.Column(db.String(50))
    especialidad = db.Column(db.String(100))
    contacto = db.Column(db.String(100))
    porcentaje_comision = db.Column(db.Float)
    recetas = db.relationship('Receta', backref='medico')

class Receta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'))
    medico_id = db.Column(db.Integer, db.ForeignKey('medico.id'))
    fecha = db.Column(db.Date)
    tipo_lente = db.Column(db.String(100))
    medida_od = db.Column(db.String(50))
    medida_os = db.Column(db.String(50))
    observaciones = db.Column(db.String(200))
    total = db.Column(db.Float)
    # Producto (armazón) asociado a la venta
    armazon_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    # Pagos relacionados
    pagos = db.relationship('Pago', backref='receta')
    venta = db.relationship('Venta', backref='receta', uselist=False)

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'))
    metodo_pago = db.Column(db.String(50))
    monto = db.Column(db.Float)
    fecha = db.Column(db.Date)

class CierreCaja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date)
    total_efectivo = db.Column(db.Float)
    total_tarjeta = db.Column(db.Float)
    total_transferencia = db.Column(db.Float)
    total_general = db.Column(db.Float)

# Nuevos modelos para pagos parciales y gastos
class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'), nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    descuento = db.Column(db.Float, default=0)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(100))
    descripcion = db.Column(db.String(200))
    monto = db.Column(db.Float, nullable=False)