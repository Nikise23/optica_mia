from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import db, Producto, Paciente, Medico, Receta, Venta, CierreCaja, Pago, Gasto
from datetime import date, datetime
from sqlalchemy import func

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

with app.app_context():
    db.create_all()
    # Lightweight SQLite migrations for existing databases
    try:
        engine_name = db.engine.name
        if engine_name == 'sqlite':
            conn = db.engine.raw_connection()
            cur = conn.cursor()
            def column_exists(table: str, column: str) -> bool:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [row[1] for row in cur.fetchall()]
                return column in cols
            # Add pago.descuento if missing
            if column_exists('pago', 'id') and not column_exists('pago', 'descuento'):
                cur.execute("ALTER TABLE pago ADD COLUMN descuento REAL DEFAULT 0")
            # Add receta.armazon_id if missing
            if column_exists('receta', 'id') and not column_exists('receta', 'armazon_id'):
                cur.execute("ALTER TABLE receta ADD COLUMN armazon_id INTEGER")
            # Add cierre_caja.estado_abierta if missing
            if column_exists('cierre_caja', 'id') and not column_exists('cierre_caja', 'estado_abierta'):
                cur.execute("ALTER TABLE cierre_caja ADD COLUMN estado_abierta BOOLEAN DEFAULT 1")
            conn.commit()
            cur.close()
            conn.close()
    except Exception as _e:
        # Avoid breaking app startup on migration issues; will surface during ops
        pass

@app.route('/')
def dashboard():
    # Productos bajo stock
    productos_bajo_stock = (
        Producto.query
        .filter(Producto.cantidad <= Producto.stock_minimo)
        .order_by(Producto.cantidad.asc())
        .limit(10)
        .all()
    )

    # Recetas del mes actual (usando año-mes para evitar errores con strftime en distintos backends)
    today = date.today()
    first_of_month = date(today.year, today.month, 1)
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    recetas_mes = (
        Receta.query
        .filter(Receta.fecha >= first_of_month, Receta.fecha < next_month)
        .count()
    )

    # Comisiones por médico basadas en pagos NETOS (con descuento aplicado)
    medicos = Medico.query.all()
    comisiones = {}
    comisiones_detalle = []
    for medico in medicos:
        # Sumar pagos netos de todas sus recetas del mes actual
        pagos_netos = 0.0
        for receta in medico.recetas:
            if receta.fecha >= first_of_month and receta.fecha < next_month:
                for p in getattr(receta, 'pagos', []) or []:
                    pagos_netos += (p.monto or 0) * (1 - ((p.descuento or 0) / 100.0))
        porcentaje = medico.porcentaje_comision or 0
        monto = pagos_netos * (porcentaje / 100.0)
        comisiones[medico.id] = monto
        comisiones_detalle.append({'medico': medico, 'porcentaje': porcentaje, 'monto': monto, 'pagos_netos': pagos_netos})

    # Cierre de hoy
    cierre_hoy = CierreCaja.query.filter_by(fecha=today).first()

    # Saldo mensual (recaudado neto - gastos)
    pagos_mes_neto = 0.0
    for p in Pago.query.filter(Pago.fecha >= first_of_month, Pago.fecha < next_month).all():
        pagos_mes_neto += (p.monto or 0) * (1 - ((p.descuento or 0) / 100.0))
    
    gastos_mes = (
        db.session.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha >= first_of_month, Gasto.fecha < next_month)
        .scalar()
    )
    saldo_mes = pagos_mes_neto - gastos_mes

    # Datos para gráfico de evolución diaria (últimos 30 días)
    from datetime import timedelta
    fecha_inicio = today - timedelta(days=29)
    datos_grafico = []
    for i in range(30):
        fecha_actual = fecha_inicio + timedelta(days=i)
        pagos_dia = Pago.query.filter_by(fecha=fecha_actual).all()
        gastos_dia = Gasto.query.filter_by(fecha=fecha_actual).all()
        
        ingresos_dia = sum((p.monto or 0) * (1 - ((p.descuento or 0) / 100.0)) for p in pagos_dia)
        gastos_dia_total = sum(g.monto or 0 for g in gastos_dia)
        saldo_dia = ingresos_dia - gastos_dia_total
        
        datos_grafico.append({
            'fecha': fecha_actual.strftime('%d/%m'),
            'ingresos': round(ingresos_dia, 2),
            'gastos': round(gastos_dia_total, 2),
            'saldo': round(saldo_dia, 2)
        })

    return render_template(
        'dashboard.html',
        productos_bajo_stock=productos_bajo_stock,
        recetas_mes=recetas_mes,
        comisiones=comisiones,
        comisiones_detalle=comisiones_detalle,
        cierre_hoy=cierre_hoy,
        saldo_mes=saldo_mes,
        pagos_mes_neto=pagos_mes_neto,
        gastos_mes=gastos_mes,
        datos_grafico=datos_grafico,
        first_of_month=first_of_month,
        next_month=next_month,
    )

# CRUD de productos, pacientes, médicos, recetas, caja...
# (Ver README para el resto del código completo por archivo)

# ---------- CRUD Productos ----------
@app.route('/productos')
def productos_list():
    query = Producto.query.order_by(Producto.nombre.asc())
    term = request.args.get('q')
    if term:
        like = f"%{term}%"
        try:
            query = query.filter((Producto.nombre.ilike(like)) | (Producto.codigo.ilike(like)))
        except Exception:
            query = query.filter((func.lower(Producto.nombre).like(like.lower())) | (func.lower(Producto.codigo).like(like.lower())))
    productos = query.all()
    return render_template('productos.html', productos=productos, term=term)


@app.route('/productos/new', methods=['GET', 'POST'])
def productos_create():
    if request.method == 'POST':
        try:
            producto = Producto(
                codigo=request.form.get('codigo', '').strip(),
                nombre=request.form.get('nombre', '').strip(),
                descripcion=(request.form.get('descripcion') or '').strip() or None,
                categoria=(request.form.get('categoria') or '').strip() or None,
                precio_unitario=float(request.form.get('precio_unitario') or 0),
                cantidad=int(request.form.get('cantidad') or 0),
                stock_minimo=int(request.form.get('stock_minimo') or 0),
            )
            db.session.add(producto)
            db.session.commit()
            flash('Producto creado correctamente')
            return redirect(url_for('productos_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al crear producto: {exc}')
    return render_template('producto_form.html', producto=None)


@app.route('/productos/<int:producto_id>/edit', methods=['GET', 'POST'])
def productos_edit(producto_id: int):
    producto = Producto.query.get_or_404(producto_id)
    if request.method == 'POST':
        try:
            producto.codigo = request.form.get('codigo', '').strip()
            producto.nombre = request.form.get('nombre', '').strip()
            producto.descripcion = (request.form.get('descripcion') or '').strip() or None
            producto.categoria = (request.form.get('categoria') or '').strip() or None
            producto.precio_unitario = float(request.form.get('precio_unitario') or 0)
            producto.cantidad = int(request.form.get('cantidad') or 0)
            producto.stock_minimo = int(request.form.get('stock_minimo') or 0)
            db.session.commit()
            flash('Producto actualizado correctamente')
            return redirect(url_for('productos_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al actualizar producto: {exc}')
    return render_template('producto_form.html', producto=producto)


@app.route('/productos/<int:producto_id>/delete', methods=['POST'])
def productos_delete(producto_id: int):
    producto = Producto.query.get_or_404(producto_id)
    try:
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo eliminar: {exc}')
    return redirect(url_for('productos_list'))

# ---------- CRUD Pacientes ----------
@app.route('/pacientes')
def pacientes_list():
    query = Paciente.query.order_by(Paciente.apellido.asc(), Paciente.nombre.asc())
    term = request.args.get('q')
    if term:
        like = f"%{term}%"
        query = query.filter(
            (Paciente.nombre.ilike(like)) |
            (Paciente.apellido.ilike(like)) |
            (Paciente.dni.ilike(like))
        )
    pacientes = query.all()
    return render_template('pacientes.html', pacientes=pacientes, term=term)


@app.route('/pacientes/new', methods=['GET', 'POST'])
def pacientes_create():
    if request.method == 'POST':
        try:
            fecha_nacimiento_str = (request.form.get('fecha_nacimiento') or '').strip()
            fecha_nacimiento_val = None
            if fecha_nacimiento_str:
                try:
                    fecha_nacimiento_val = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Fecha de nacimiento inválida. Use AAAA-MM-DD')
                    return render_template('paciente_form.html', paciente=None)
            paciente = Paciente(
                nombre=request.form.get('nombre', '').strip(),
                apellido=request.form.get('apellido', '').strip(),
                dni=request.form.get('dni', '').strip(),
                fecha_nacimiento=fecha_nacimiento_val,
                obra_social=(request.form.get('obra_social') or '').strip() or None,
                contacto=(request.form.get('contacto') or '').strip() or None,
            )
            db.session.add(paciente)
            db.session.commit()
            flash('Paciente creado correctamente')
            return redirect(url_for('pacientes_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al crear paciente: {exc}')
    return render_template('paciente_form.html', paciente=None)


@app.route('/pacientes/<int:paciente_id>/edit', methods=['GET', 'POST'])
def pacientes_edit(paciente_id: int):
    paciente = Paciente.query.get_or_404(paciente_id)
    if request.method == 'POST':
        try:
            paciente.nombre = request.form.get('nombre', '').strip()
            paciente.apellido = request.form.get('apellido', '').strip()
            paciente.dni = request.form.get('dni', '').strip()
            fecha_nacimiento_str = (request.form.get('fecha_nacimiento') or '').strip()
            if fecha_nacimiento_str:
                try:
                    paciente.fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Fecha de nacimiento inválida. Use AAAA-MM-DD')
                    return render_template('paciente_form.html', paciente=paciente)
            else:
                paciente.fecha_nacimiento = None
            paciente.obra_social = (request.form.get('obra_social') or '').strip() or None
            paciente.contacto = (request.form.get('contacto') or '').strip() or None
            db.session.commit()
            flash('Paciente actualizado correctamente')
            return redirect(url_for('pacientes_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al actualizar paciente: {exc}')
    return render_template('paciente_form.html', paciente=paciente)


@app.route('/pacientes/<int:paciente_id>/delete', methods=['POST'])
def pacientes_delete(paciente_id: int):
    paciente = Paciente.query.get_or_404(paciente_id)
    try:
        db.session.delete(paciente)
        db.session.commit()
        flash('Paciente eliminado')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo eliminar: {exc}')
    return redirect(url_for('pacientes_list'))

# ---------- CRUD Médicos ----------
@app.route('/medicos')
def medicos_list():
    query = Medico.query.order_by(Medico.apellido.asc(), Medico.nombre.asc())
    term = request.args.get('q')
    if term:
        like = f"%{term}%"
        query = query.filter(
            (Medico.nombre.ilike(like)) |
            (Medico.apellido.ilike(like)) |
            (Medico.matricula.ilike(like)) |
            (Medico.especialidad.ilike(like))
        )
    medicos = query.all()
    return render_template('medicos.html', medicos=medicos, term=term)


@app.route('/medicos/new', methods=['GET', 'POST'])
def medicos_create():
    if request.method == 'POST':
        try:
            medico = Medico(
                nombre=request.form.get('nombre', '').strip(),
                apellido=request.form.get('apellido', '').strip(),
                matricula=request.form.get('matricula', '').strip(),
                especialidad=(request.form.get('especialidad') or '').strip() or None,
                contacto=(request.form.get('contacto') or '').strip() or None,
                porcentaje_comision=float(request.form.get('porcentaje_comision') or 0),
            )
            db.session.add(medico)
            db.session.commit()
            flash('Médico creado correctamente')
            return redirect(url_for('medicos_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al crear médico: {exc}')
    return render_template('medico_form.html', medico=None)


@app.route('/medicos/<int:medico_id>/edit', methods=['GET', 'POST'])
def medicos_edit(medico_id: int):
    medico = Medico.query.get_or_404(medico_id)
    if request.method == 'POST':
        try:
            medico.nombre = request.form.get('nombre', '').strip()
            medico.apellido = request.form.get('apellido', '').strip()
            medico.matricula = request.form.get('matricula', '').strip()
            medico.especialidad = (request.form.get('especialidad') or '').strip() or None
            medico.contacto = (request.form.get('contacto') or '').strip() or None
            medico.porcentaje_comision = float(request.form.get('porcentaje_comision') or 0)
            db.session.commit()
            flash('Médico actualizado correctamente')
            return redirect(url_for('medicos_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al actualizar médico: {exc}')
    return render_template('medico_form.html', medico=medico)


@app.route('/medicos/<int:medico_id>/delete', methods=['POST'])
def medicos_delete(medico_id: int):
    medico = Medico.query.get_or_404(medico_id)
    try:
        db.session.delete(medico)
        db.session.commit()
        flash('Médico eliminado')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo eliminar: {exc}')
    return redirect(url_for('medicos_list'))

# ---------- CRUD Recetas ----------
@app.route('/recetas')
def recetas_list():
    from sqlalchemy.orm import joinedload
    query = Receta.query.options(joinedload(Receta.paciente), joinedload(Receta.medico)).order_by(Receta.fecha.desc())
    term = request.args.get('q')
    if term:
        like = f"%{term}%"
        query = query.join(Paciente).outerjoin(Medico).filter(
            (Paciente.nombre.ilike(like)) |
            (Paciente.apellido.ilike(like)) |
            (Medico.nombre.ilike(like)) |
            (Medico.apellido.ilike(like)) |
            (Receta.tipo_lente.ilike(like))
        )
    recetas = query.all()
    return render_template('recetas.html', recetas=recetas, term=term)


@app.route('/recetas/new', methods=['GET', 'POST'])
def recetas_create():
    if request.method == 'POST':
        try:
            fecha_str = (request.form.get('fecha') or '').strip()
            fecha_val = None
            if fecha_str:
                try:
                    fecha_val = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Fecha inválida. Use AAAA-MM-DD')
                    return render_template('receta_form.html', receta=None, medicos=Medico.query.all(), pacientes=Paciente.query.all(), armazones=Producto.query.order_by(Producto.nombre.asc()).all())
            else:
                fecha_val = date.today()
            
            # Manejar médico opcional
            medico_id_val = request.form.get('medico_id', '').strip()
            medico_id = int(medico_id_val) if medico_id_val else None
            
            receta = Receta(
                paciente_id=int(request.form.get('paciente_id') or 0),
                medico_id=medico_id,
                fecha=fecha_val,
                tipo_lente=(request.form.get('tipo_lente') or '').strip() or None,
                medida_od=(request.form.get('medida_od') or '').strip() or None,
                medida_os=(request.form.get('medida_os') or '').strip() or None,
                observaciones=(request.form.get('observaciones') or '').strip() or None,
                total=float(request.form.get('total') or 0),
            )
            db.session.add(receta)
            # Descontar stock armazón si corresponde
            armazon_id_val = request.form.get('armazon_id')
            if armazon_id_val:
                armazon = Producto.query.get(int(armazon_id_val))
                if armazon and armazon.cantidad > 0:
                    armazon.cantidad -= 1
                    receta.armazon_id = armazon.id
                else:
                    raise Exception('Sin stock disponible para el armazón seleccionado')
            db.session.commit()
            flash('Receta creada correctamente')
            return redirect(url_for('recetas_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al crear receta: {exc}')
    return render_template('receta_form.html', receta=None, medicos=Medico.query.all(), pacientes=Paciente.query.all(), armazones=Producto.query.order_by(Producto.nombre.asc()).all())


@app.route('/recetas/<int:receta_id>/edit', methods=['GET', 'POST'])
def recetas_edit(receta_id: int):
    receta = Receta.query.get_or_404(receta_id)
    if request.method == 'POST':
        try:
            receta.paciente_id = int(request.form.get('paciente_id') or 0)
            # Manejar médico opcional
            medico_id_val = request.form.get('medico_id', '').strip()
            receta.medico_id = int(medico_id_val) if medico_id_val else None
            fecha_str = (request.form.get('fecha') or '').strip()
            if fecha_str:
                try:
                    receta.fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Fecha inválida. Use AAAA-MM-DD')
                    return render_template('receta_form.html', receta=receta, medicos=Medico.query.all(), pacientes=Paciente.query.all())
            receta.tipo_lente = (request.form.get('tipo_lente') or '').strip() or None
            receta.medida_od = (request.form.get('medida_od') or '').strip() or None
            receta.medida_os = (request.form.get('medida_os') or '').strip() or None
            receta.observaciones = (request.form.get('observaciones') or '').strip() or None
            receta.total = float(request.form.get('total') or 0)
            # Manejar armazón y stock
            new_armazon_id = int(request.form.get('armazon_id')) if request.form.get('armazon_id') else None
            if new_armazon_id != getattr(receta, 'armazon_id', None):
                if getattr(receta, 'armazon_id', None):
                    prev = Producto.query.get(receta.armazon_id)
                    if prev:
                        prev.cantidad += 1
                if new_armazon_id:
                    nuevo = Producto.query.get(new_armazon_id)
                    if nuevo and nuevo.cantidad > 0:
                        nuevo.cantidad -= 1
                    else:
                        raise Exception('Sin stock disponible para el armazón seleccionado')
            receta.armazon_id = new_armazon_id
            db.session.commit()
            flash('Receta actualizada correctamente')
            return redirect(url_for('recetas_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al actualizar receta: {exc}')
    return render_template('receta_form.html', receta=receta, medicos=Medico.query.all(), pacientes=Paciente.query.all(), armazones=Producto.query.order_by(Producto.nombre.asc()).all())


@app.route('/recetas/<int:receta_id>/delete', methods=['POST'])
def recetas_delete(receta_id: int):
    receta = Receta.query.get_or_404(receta_id)
    try:
        db.session.delete(receta)
        db.session.commit()
        flash('Receta eliminada')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo eliminar: {exc}')
    return redirect(url_for('recetas_list'))

# ---------- Caja (Pagos parciales, Gastos, Cierres) ----------
@app.route('/caja')
def caja_dashboard():
    # Fecha de referencia
    hoy = date.today()

    # Pagos del día
    pagos_hoy = Pago.query.filter_by(fecha=hoy).all()

    # Resumen por método de pago (neto por pago con descuento %)
    resumen_metodos = {}
    for pago in pagos_hoy:
        metodo = pago.metodo_pago or 'Sin especificar'
        if metodo not in resumen_metodos:
            resumen_metodos[metodo] = 0
        descuento_pct = (pago.descuento or 0) / 100.0
        resumen_metodos[metodo] += (pago.monto or 0) * (1 - descuento_pct)

    # Gastos del día
    gastos_hoy = Gasto.query.filter_by(fecha=hoy).all()
    total_gastos_hoy = sum(g.monto or 0 for g in gastos_hoy)

    # Cierre de caja de hoy - apertura automática si no existe
    cierre_hoy = CierreCaja.query.filter_by(fecha=hoy).first()
    if not cierre_hoy:
        # Crear cierre automático para hoy (abierto)
        cierre_hoy = CierreCaja(
            fecha=hoy,
            total_efectivo=0,
            total_tarjeta=0,
            total_transferencia=0,
            total_general=0,
            estado_abierta=True
        )
        db.session.add(cierre_hoy)
        db.session.commit()
        flash('Caja abierta automáticamente para hoy', 'info')

    # Recetas finalizadas (completamente pagadas)
    from sqlalchemy.orm import joinedload
    recetas_finalizadas = []
    recetas_pendientes = []
    
    for r in Receta.query.options(joinedload(Receta.paciente), joinedload(Receta.medico)).all():
        pagos_brutos = sum((p.monto or 0) for p in getattr(r, 'pagos', []) or [])
        saldo_restante = max(0.0, (r.total or 0) - pagos_brutos)
        
        # Calcular descuento aplicado comparando con el total original
        descuento_pct = r.pagos[0].descuento if r.pagos and r.pagos[0].descuento > 0 else 0
        if descuento_pct > 0:
            total_original = r.total / (1 - (descuento_pct / 100.0))
        else:
            total_original = r.total
            
        receta_data = {
            'receta': r,
            'total_original': total_original,
            'descuento_pct': descuento_pct,
            'total_final': r.total,
            'pagado': pagos_brutos,
            'saldo': saldo_restante
        }
        
        if saldo_restante <= 1e-6:  # Receta completamente pagada
            recetas_finalizadas.append(receta_data)
        else:  # Receta con saldo pendiente
            recetas_pendientes.append(receta_data)
    
    # Ordenar por fecha de último pago
    recetas_finalizadas.sort(key=lambda x: max(p.fecha for p in x['receta'].pagos) if x['receta'].pagos else x['receta'].fecha, reverse=True)
    recetas_finalizadas = recetas_finalizadas[:10]  # Últimas 10
    
    recetas_pendientes.sort(key=lambda x: max(p.fecha for p in x['receta'].pagos) if x['receta'].pagos else x['receta'].fecha, reverse=True)
    recetas_pendientes = recetas_pendientes[:10]  # Últimas 10

    # Recaudación mensual (pagos) y gastos mensuales
    first_of_month = date(hoy.year, hoy.month, 1)
    next_month = date(hoy.year + (1 if hoy.month == 12 else 0), (1 if hoy.month == 12 else hoy.month + 1), 1)
    # Sumatoria neta mensual (aplicando descuento %)
    pagos_mes = 0.0
    for p in Pago.query.filter(Pago.fecha >= first_of_month, Pago.fecha < next_month).all():
        pagos_mes += (p.monto or 0) * (1 - ((p.descuento or 0) / 100.0))
    gastos_mes = (
        db.session.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha >= first_of_month, Gasto.fecha < next_month)
        .scalar()
    )

    return render_template(
        'caja.html',
        pagos_hoy=pagos_hoy,
        resumen_metodos=resumen_metodos,
        gastos_hoy=gastos_hoy,
        total_gastos_hoy=total_gastos_hoy,
        cierre_hoy=cierre_hoy,
        recetas_finalizadas=recetas_finalizadas,
        recetas_pendientes=recetas_pendientes,
        pagos_mes=pagos_mes,
        gastos_mes=gastos_mes,
    )


@app.route('/caja/pago/new', methods=['GET', 'POST'])
def caja_pago_create():
    # Verificar si la caja está abierta
    hoy = date.today()
    cierre_hoy = CierreCaja.query.filter_by(fecha=hoy).first()
    if cierre_hoy and not cierre_hoy.estado_abierta:
        flash('La caja está cerrada. Debe reabrirla para registrar pagos.', 'warning')
        return redirect(url_for('caja_dashboard'))
    
    if request.method == 'POST':
        try:
            receta_id_val = int(request.form.get('receta_id') or 0)
            monto_val = float(request.form.get('monto') or 0)
            descuento_pct = float(request.form.get('descuento') or 0)
            if descuento_pct < 0 or descuento_pct > 100:
                raise Exception('El descuento debe estar entre 0 y 100%')
            # Validar saldo restante de la receta
            receta = Receta.query.get_or_404(receta_id_val)
            pagos_existentes = Pago.query.filter_by(receta_id=receta.id).all()

            # Si es el primer pago con descuento, aplicar el descuento al total de la receta
            if len(pagos_existentes) == 0 and descuento_pct > 0:
                receta.total = (receta.total or 0) * (1 - (descuento_pct / 100.0))
                # Mantener el descuento original en el pago para registro histórico

            # Calcular saldo restante considerando que el total ya puede tener descuento aplicado
            total_pagado_bruto = sum((px.monto or 0) for px in pagos_existentes)
            saldo_restante = (receta.total or 0) - total_pagado_bruto
            
            # Validar que el monto no supere el saldo restante
            if monto_val > saldo_restante + 1e-6:
                raise Exception('El monto supera el saldo restante de la receta')

            pago = Pago(
                receta_id=receta.id,
                metodo_pago=request.form.get('metodo_pago', '').strip(),
                monto=monto_val,
                fecha=date.today(),
                descuento=descuento_pct,
            )
            db.session.add(pago)
            db.session.commit()
            flash('Pago registrado correctamente')
            return redirect(url_for('caja_dashboard'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al registrar pago: {exc}')
    
    # Obtener recetas con saldo pendiente (no completamente pagadas)
    from sqlalchemy.orm import joinedload
    recetas_con_saldo = []
    for r in Receta.query.options(joinedload(Receta.paciente), joinedload(Receta.medico)).all():
        pagos_brutos = sum((p.monto or 0) for p in getattr(r, 'pagos', []) or [])
        saldo_restante = max(0.0, (r.total or 0) - pagos_brutos)
        if saldo_restante > 1e-6:  # Tolerancia para redondeos
            recetas_con_saldo.append({'receta': r, 'restante': saldo_restante, 'pagado_neto': pagos_brutos})
    
    return render_template('pago_form.html', recetas_con_saldo=recetas_con_saldo)


@app.route('/caja/cierre/new', methods=['GET', 'POST'])
def caja_cierre_create():
    if request.method == 'POST':
        try:
            # Verificar si ya existe cierre para hoy
            hoy = date.today()
            cierre_existente = CierreCaja.query.filter_by(fecha=hoy).first()
            if cierre_existente and not cierre_existente.estado_abierta:
                flash('Ya existe un cierre de caja para hoy')
                return redirect(url_for('caja_dashboard'))
            
            # Calcular totales del día
            pagos_hoy = Pago.query.filter_by(fecha=hoy).all()
            total_efectivo = sum((p.monto or 0) * (1 - ((p.descuento or 0) / 100.0)) for p in pagos_hoy if p.metodo_pago == 'Efectivo')
            total_tarjeta = sum((p.monto or 0) * (1 - ((p.descuento or 0) / 100.0)) for p in pagos_hoy if p.metodo_pago == 'Tarjeta')
            total_transferencia = sum((p.monto or 0) * (1 - ((p.descuento or 0) / 100.0)) for p in pagos_hoy if p.metodo_pago == 'Transferencia')
            total_general = sum((p.monto or 0) * (1 - ((p.descuento or 0) / 100.0)) for p in pagos_hoy)
            
            if cierre_existente:
                # Actualizar cierre existente
                cierre_existente.total_efectivo = total_efectivo
                cierre_existente.total_tarjeta = total_tarjeta
                cierre_existente.total_transferencia = total_transferencia
                cierre_existente.total_general = total_general
                cierre_existente.estado_abierta = False
            else:
                # Crear nuevo cierre
                cierre = CierreCaja(
                    fecha=hoy,
                    total_efectivo=total_efectivo,
                    total_tarjeta=total_tarjeta,
                    total_transferencia=total_transferencia,
                    total_general=total_general,
                    estado_abierta=False
                )
                db.session.add(cierre)
            
            db.session.commit()
            flash('Caja cerrada correctamente')
            return redirect(url_for('caja_dashboard'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al cerrar caja: {exc}')
    
    return render_template('cierre_form.html')


@app.route('/caja/reabrir', methods=['POST'])
def caja_reabrir():
    try:
        hoy = date.today()
        cierre_hoy = CierreCaja.query.filter_by(fecha=hoy).first()
        if not cierre_hoy:
            flash('No hay cierre de caja para hoy')
            return redirect(url_for('caja_dashboard'))
        
        cierre_hoy.estado_abierta = True
        db.session.commit()
        flash('Caja reabierta correctamente')
        return redirect(url_for('caja_dashboard'))
    except Exception as exc:
        db.session.rollback()
        flash(f'Error al reabrir caja: {exc}')
        return redirect(url_for('caja_dashboard'))


@app.route('/caja/pago/<int:pago_id>/delete', methods=['POST'])
def caja_pago_delete(pago_id: int):
    pago = Pago.query.get_or_404(pago_id)
    try:
        db.session.delete(pago)
        db.session.commit()
        flash('Pago eliminado')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo eliminar: {exc}')
    return redirect(url_for('caja_dashboard'))

# Gastos
@app.route('/gastos')
def gastos_list():
    query = Gasto.query.order_by(Gasto.fecha.desc())
    gastos = query.all()
    return render_template('gastos.html', gastos=gastos)

@app.route('/gastos/new', methods=['GET', 'POST'])
def gastos_create():
    # Verificar si la caja está abierta
    hoy = date.today()
    cierre_hoy = CierreCaja.query.filter_by(fecha=hoy).first()
    if cierre_hoy and not cierre_hoy.estado_abierta:
        flash('La caja está cerrada. Debe reabrirla para registrar gastos.', 'warning')
        return redirect(url_for('gastos_list'))
    
    if request.method == 'POST':
        try:
            fecha_str = (request.form.get('fecha') or '').strip()
            fecha_val = date.today()
            if fecha_str:
                fecha_val = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            gasto = Gasto(
                fecha=fecha_val,
                categoria=(request.form.get('categoria') or '').strip() or None,
                descripcion=(request.form.get('descripcion') or '').strip() or None,
                monto=float(request.form.get('monto') or 0),
            )
            db.session.add(gasto)
            db.session.commit()
            flash('Gasto registrado correctamente')
            return redirect(url_for('gastos_list'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Error al registrar gasto: {exc}')
    return render_template('gasto_form.html', gasto=None)

@app.route('/gastos/<int:gasto_id>/delete', methods=['POST'])
def gastos_delete(gasto_id: int):
    gasto = Gasto.query.get_or_404(gasto_id)
    try:
        db.session.delete(gasto)
        db.session.commit()
        flash('Gasto eliminado')
    except Exception as exc:
        db.session.rollback()
        flash(f'No se pudo eliminar: {exc}')
    return redirect(url_for('gastos_list'))


@app.route('/reporte-diario')
def reporte_diario():
    # Obtener fecha del parámetro o usar hoy
    fecha_str = request.args.get('fecha')
    if fecha_str:
        try:
            fecha_consulta = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_consulta = date.today()
    else:
        fecha_consulta = date.today()
    
    # Pagos del día
    pagos_dia = Pago.query.filter_by(fecha=fecha_consulta).all()
    total_pagos_dia = sum((p.monto or 0) for p in pagos_dia)
    
    # Gastos del día
    gastos_dia = Gasto.query.filter_by(fecha=fecha_consulta).all()
    total_gastos_dia = sum((g.monto or 0) for g in gastos_dia)
    
    # Cierre de caja del día
    cierre_dia = CierreCaja.query.filter_by(fecha=fecha_consulta).first()
    
    # Resumen por método de pago
    resumen_metodos = {}
    for pago in pagos_dia:
        metodo = pago.metodo_pago or 'Sin especificar'
        if metodo not in resumen_metodos:
            resumen_metodos[metodo] = 0
        resumen_metodos[metodo] += pago.monto or 0
    
    # Recetas del día (agrupadas)
    recetas_dia = []
    recetas_con_pagos = db.session.query(Receta).join(Pago).filter(Pago.fecha == fecha_consulta).distinct().all()
    
    for r in recetas_con_pagos:
        pagos_receta = Pago.query.filter(Pago.receta_id == r.id, Pago.fecha == fecha_consulta).all()
        total_pagado_dia = sum((p.monto or 0) for p in pagos_receta)
        
        # Calcular descuento aplicado
        descuento_pct = r.pagos[0].descuento if r.pagos and r.pagos[0].descuento > 0 else 0
        if descuento_pct > 0:
            total_original = r.total / (1 - (descuento_pct / 100.0))
        else:
            total_original = r.total
        
        # Calcular saldos
        total_pagado_total = sum((p.monto or 0) for p in r.pagos)
        saldo_pendiente = max(0.0, (r.total or 0) - total_pagado_total)
        
        # Métodos de pago del día
        metodos_dia = list(set(p.metodo_pago or 'Sin especificar' for p in pagos_receta))
        
        recetas_dia.append({
            'receta': r,
            'total_original': total_original,
            'descuento_pct': descuento_pct,
            'total_final': r.total,
            'pagado_dia': total_pagado_dia,
            'pagado_total': total_pagado_total,
            'saldo_pendiente': saldo_pendiente,
            'metodo': ', '.join(metodos_dia)
        })
    
    # Ordenar por fecha
    recetas_dia.sort(key=lambda x: x['receta'].fecha, reverse=True)
    
    return render_template(
        'reporte_diario.html',
        fecha_consulta=fecha_consulta,
        pagos_dia=pagos_dia,
        total_pagos_dia=total_pagos_dia,
        gastos_dia=gastos_dia,
        total_gastos_dia=total_gastos_dia,
        cierre_dia=cierre_dia,
        resumen_metodos=resumen_metodos,
        recetas_dia=recetas_dia
    )


@app.route('/reporte-mensual')
def reporte_mensual():
    # Obtener mes y año del parámetro o usar actual
    mes = request.args.get('mes', date.today().month, type=int)
    año = request.args.get('año', date.today().year, type=int)
    
    hoy = date(año, mes, 1)
    first_of_month = date(hoy.year, hoy.month, 1)
    if hoy.month == 12:
        next_month = date(hoy.year + 1, 1, 1)
    else:
        next_month = date(hoy.year, hoy.month + 1, 1)
    
    # Recaudación neta del mes - agrupado por receta
    pagos_mes_neto = 0.0
    recetas_detalle = []
    
    # Obtener recetas que tuvieron pagos en el mes
    recetas_con_pagos = db.session.query(Receta).join(Pago).filter(
        Pago.fecha >= first_of_month, 
        Pago.fecha < next_month
    ).distinct().all()
    
    for r in recetas_con_pagos:
        # Pagos de esta receta en el mes
        pagos_receta = Pago.query.filter(
            Pago.receta_id == r.id,
            Pago.fecha >= first_of_month, 
            Pago.fecha < next_month
        ).all()
        
        # Calcular totales
        total_pagado_mes = sum((p.monto or 0) for p in pagos_receta)
        pagos_mes_neto += total_pagado_mes
        
        # Calcular descuento aplicado
        descuento_pct = r.pagos[0].descuento if r.pagos and r.pagos[0].descuento > 0 else 0
        if descuento_pct > 0:
            total_original = r.total / (1 - (descuento_pct / 100.0))
        else:
            total_original = r.total
        
        # Calcular saldos
        total_pagado_total = sum((p.monto or 0) for p in r.pagos)
        saldo_pendiente = max(0.0, (r.total or 0) - total_pagado_total)
        
        # Métodos de pago del mes (únicos)
        metodos_mes = list(set(p.metodo_pago or 'Sin especificar' for p in pagos_receta))
        
        recetas_detalle.append({
            'fecha': r.fecha,
            'paciente': f"{r.paciente.apellido}, {r.paciente.nombre}",
            'medico': f"{r.medico.apellido}, {r.medico.nombre}" if r.medico else "Sin médico",
            'metodo': ', '.join(metodos_mes),
            'total_original': total_original,
            'descuento': descuento_pct,
            'total_final': r.total,
            'pagado_mes': total_pagado_mes,
            'pagado_total': total_pagado_total,
            'saldo_pendiente': saldo_pendiente
        })
    
    # Ordenar por fecha
    recetas_detalle.sort(key=lambda x: x['fecha'], reverse=True)
    
    # Gastos del mes
    gastos_mes = (
        db.session.query(func.coalesce(func.sum(Gasto.monto), 0))
        .filter(Gasto.fecha >= first_of_month, Gasto.fecha < next_month)
        .scalar()
    )
    gastos_detalle = Gasto.query.filter(Gasto.fecha >= first_of_month, Gasto.fecha < next_month).order_by(Gasto.fecha.desc()).all()
    
    # Comisiones por médico del mes
    medicos = Medico.query.all()
    comisiones_detalle = []
    total_comisiones = 0.0
    for medico in medicos:
        pagos_netos = 0.0
        for receta in medico.recetas:
            if receta.fecha >= first_of_month and receta.fecha < next_month:
                for p in getattr(receta, 'pagos', []) or []:
                    pagos_netos += (p.monto or 0) * (1 - ((p.descuento or 0) / 100.0))
        porcentaje = medico.porcentaje_comision or 0
        monto_comision = pagos_netos * (porcentaje / 100.0)
        total_comisiones += monto_comision
        if pagos_netos > 0:  # Solo mostrar médicos con ventas
            comisiones_detalle.append({
                'medico': medico,
                'porcentaje': porcentaje,
                'pagos_netos': pagos_netos,
                'comision': monto_comision
            })
    
    # Resumen final
    saldo_mes = pagos_mes_neto - gastos_mes - total_comisiones
    
    from datetime import timedelta
    
    return render_template(
        'reporte_mensual.html',
        first_of_month=first_of_month,
        next_month=next_month,
        pagos_mes_neto=pagos_mes_neto,
        recetas_detalle=recetas_detalle,
        gastos_mes=gastos_mes,
        gastos_detalle=gastos_detalle,
        comisiones_detalle=comisiones_detalle,
        total_comisiones=total_comisiones,
        saldo_mes=saldo_mes,
        timedelta=timedelta,
    )


# CSV export del cierre diario
from flask import Response

@app.route('/caja/cierre/csv')
def caja_cierre_csv():
    fecha_str = request.args.get('fecha')
    if fecha_str:
        try:
            dia = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            dia = date.today()
    else:
        dia = date.today()

    pagos = Pago.query.filter_by(fecha=dia).all()
    gastos = Gasto.query.filter_by(fecha=dia).all()

    # Construir CSV
    import csv
    from io import StringIO
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(['Tipo', 'Fecha', 'Paciente', 'Medico', 'Metodo', 'Monto', 'Detalle'])
    for p in pagos:
        paciente_nombre = getattr(getattr(p, 'receta', None), 'paciente', None)
        medico_nombre = getattr(getattr(p, 'receta', None), 'medico', None)
        paciente_txt = f"{getattr(paciente_nombre, 'apellido', '')}, {getattr(paciente_nombre, 'nombre', '')}" if paciente_nombre else ''
        medico_txt = f"{getattr(medico_nombre, 'apellido', '')}, {getattr(medico_nombre, 'nombre', '')}" if medico_nombre else ''
        writer.writerow(['Pago', p.fecha, paciente_txt, medico_txt, p.metodo_pago, p.monto, f"Receta #{p.receta_id}"])
    for g in gastos:
        writer.writerow(['Gasto', g.fecha, '', '', '', -g.monto, f"{g.categoria or ''} - {g.descripcion or ''}"])

    csv_data = buffer.getvalue()
    buffer.close()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=cierre_{dia.isoformat()}.csv'}
    )

if __name__ == '__main__':
    app.run(debug=True)