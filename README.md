# 🧿 ÓpticaApp

Sistema web para gestión integral de ópticas: productos, pacientes, médicos, recetas, caja, pagos parciales, gastos y dashboard con métricas.

## 🚀 Tecnologías

- **Backend**: Flask (3.x) + SQLAlchemy (2.x) + Flask-SQLAlchemy
- **Base de datos**: SQLite
- **Frontend**: Jinja2 + Bootstrap 5 + Chart.js
- **ORM**: SQLAlchemy

## 📦 Funcionalidades principales

- Productos: CRUD con control de stock y alertas de bajo stock
- Pacientes y Médicos: CRUD, comisiones por médico
- Recetas: vinculadas a paciente y médico; armazón descuenta stock
- Caja:
  - Pagos parciales por receta (señas) con descuento en %
  - Totales diarios y mensuales por método, cálculo con montos netos
  - Cierre diario y exportación CSV (pagos y gastos del día)
- Gastos: registro y listado de egresos
- Dashboard: KPIs, saldo mensual (recaudado neto − gastos), gráfico de evolución diaria

## 🗂️ Estructura del proyecto

```
optica_mia/
├── app.py
├── config.py
├── models/
│   └── models.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── productos.html / producto_form.html
│   ├── pacientes.html / paciente_form.html
│   ├── medicos.html / medico_form.html
│   ├── recetas.html / receta_form.html
│   ├── caja.html / pago_form.html / cierre_form.html
│   └── gastos.html / gasto_form.html
├── static/
│   └── styles.css
├── seeds.sql
├── requirements.txt
└── README.md
```

## 🔧 Configuración y ejecución

1) Crear venv e instalar dependencias
```
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Variables de entorno (opcional)
```
SECRET_KEY=tu-clave
DATABASE_URL=sqlite:///optica.db
FLASK_ENV=development
```

3) Ejecutar
```
set FLASK_APP=app.py
flask run
```

4) Semillas (opcional)
```
sqlite3 optica.db ".read seeds.sql"
```

## 💳 Flujo de pagos con descuento

1. Crear receta con total (ej. 165000)
2. Caja → Nuevo pago: aplicar descuento en % (ej. 20%) → total pasa a 132000
3. Elegir pago total o parcial:
   - Total: autocompleta y bloquea el monto con el restante neto
   - Parcial: monto editable; valida no exceder el saldo restante
4. Cuando el saldo llega a 0, la receta ya no aparece en el selector
5. Comisiones de médico se calculan sobre pagos netos cobrados

## 🖼️ Carpeta `static/`

- Contiene recursos estáticos servidos tal cual por Flask: CSS, imágenes, JavaScript propio, logos, etc.
- El archivo `static/styles.css` está ahí para tus estilos personalizados. Hoy puede estar vacío, pero sirve como hook para agregar detalles visuales más adelante.
- Podés borrar `styles.css` si no lo usás; si eliminás toda la carpeta `static/` también podés hacerlo, pero recordá remover referencias en `templates/base.html`:
  - `<link href="{{ url_for('static', filename='styles.css') }}" rel="stylesheet">`
  Si más adelante querés sumar estilos o assets, recreá `static/` y ese link.

## 📤 Exportación CSV del cierre

- Endpoint: `/caja/cierre/csv?fecha=AAAA-MM-DD` (si no se indica fecha, usa hoy)
- Incluye pagos (método, monto) y gastos del día

## 📝 Notas

- Se agregan migraciones livianas automáticas para columnas nuevas en SQLite (ej. `pago.descuento`, `receta.armazon_id`).
- Si cambiás la base, reiniciar la app aplica el ajuste.
