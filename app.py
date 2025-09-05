from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import db, Producto, Paciente, Medico, Receta, Venta, CierreCaja
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    productos_bajo_stock = Producto.query.filter(Producto.cantidad <= Producto.stock_minimo).all()
    recetas_mes = Receta.query.filter(func.strftime('%m', Receta.fecha) == datetime.now().strftime('%m')).count()
    medicos = Medico.query.all()
    comisiones = {m.id: sum(r.total * m.porcentaje_comision / 100 for r in m.recetas) for m in medicos}
    cierre_hoy = CierreCaja.query.filter_by(fecha=datetime.now().date()).first()
    return render_template('dashboard.html', productos_bajo_stock=productos_bajo_stock, recetas_mes=recetas_mes, comisiones=comisiones, cierre_hoy=cierre_hoy)

# CRUD de productos, pacientes, médicos, recetas, caja...
# (Ver README para el resto del código completo por archivo)

if __name__ == '__main__':
    app.run(debug=True)