import os, uuid, secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import or_

load_dotenv()
BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)), SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL','postgresql+psycopg://nerio:nerio@localhost:5432/nerio360'), SQLALCHEMY_TRACK_MODIFICATIONS=False, MAX_CONTENT_LENGTH=8*1024*1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE')=='1')
app.config['UPLOAD_FOLDER'] = str(BASE/'static'/'uploads')
db = SQLAlchemy(app)

class Admin(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(180),unique=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)

class Property(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(160),nullable=False)
    city=db.Column(db.String(120),nullable=False)
    address=db.Column(db.String(240),nullable=False)
    description=db.Column(db.Text,nullable=False)
    price=db.Column(db.BigInteger,nullable=False)
    bedrooms=db.Column(db.Integer,default=0)
    bathrooms=db.Column(db.Integer,default=0)
    area=db.Column(db.Integer,default=0)
    latitude=db.Column(db.Float,nullable=False)
    longitude=db.Column(db.Float,nullable=False)
    status=db.Column(db.String(20),default='disponible')
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    photos=db.relationship('Photo',cascade='all, delete-orphan',backref='property',lazy=True)

class Photo(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    property_id=db.Column(db.Integer,db.ForeignKey('property.id'),nullable=False)
    filename=db.Column(db.String(255),nullable=False)

class Lead(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    property_id=db.Column(db.Integer,db.ForeignKey('property.id'),nullable=False)
    property=db.relationship('Property')
    name=db.Column(db.String(140),nullable=False)
    email=db.Column(db.String(180),nullable=False)
    phone=db.Column(db.String(40),nullable=False)
    budget=db.Column(db.BigInteger,nullable=True)
    interest=db.Column(db.String(30),nullable=False)
    message=db.Column(db.Text,default='')
    preferred_date=db.Column(db.Date,nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

class Appointment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    lead_id=db.Column(db.Integer,db.ForeignKey('lead.id'),nullable=False)
    lead=db.relationship('Lead')
    scheduled_at=db.Column(db.DateTime,nullable=False)
    status=db.Column(db.String(30),default='confirmada')
    notes=db.Column(db.Text,default='')

@app.template_filter('cop')
def cop(value): return '$' + f'{int(value or 0):,}'.replace(',','.')

@app.context_processor
def csrf_context():
    if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(32)
    return {'csrf_token':session['csrf']}

@app.before_request
def check_csrf():
    if request.method in ('POST','PUT','PATCH','DELETE') and not secrets.compare_digest(request.form.get('csrf_token',''),session.get('csrf','')):
        abort(400,'Formulario inválido. Recarga la página.')

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not session.get('admin_id'): return redirect(url_for('login'))
        return fn(*args,**kwargs)
    return wrapper

def integer(name, default=0):
    try: return int(request.form.get(name) or default)
    except (ValueError,TypeError): abort(400,'Número inválido')

def save_photos(prop):
    allowed={'jpg','jpeg','png','webp'}
    for file in request.files.getlist('photos')[:8]:
        if not file or not file.filename: continue
        ext=secure_filename(file.filename).rsplit('.',1)[-1].lower()
        if ext not in allowed: abort(400,'Formato de imagen no permitido')
        from PIL import Image, UnidentifiedImageError
        try:
            image=Image.open(file.stream)
            image.verify()
            file.stream.seek(0)
            image=Image.open(file.stream).convert('RGB')
            image.thumbnail((1800,1800))
        except (UnidentifiedImageError,OSError,ValueError): abort(400,'Imagen no válida')
        name=f'{uuid.uuid4().hex}.jpg'
        image.save(Path(app.config['UPLOAD_FOLDER'])/name,'JPEG',quality=84,optimize=True)
        db.session.add(Photo(property=prop,filename=name))

def fill_property(prop):
    prop.title=request.form['title'].strip()[:160]
    prop.city=request.form['city'].strip()[:120]
    prop.address=request.form['address'].strip()[:240]
    prop.description=request.form['description'].strip()[:10000]
    prop.price=integer('price')
    prop.bedrooms=integer('bedrooms')
    prop.bathrooms=integer('bathrooms')
    prop.area=integer('area')
    try:
        prop.latitude=float(request.form['latitude']);prop.longitude=float(request.form['longitude'])
    except ValueError: abort(400,'Coordenadas inválidas')
    if not (-90<=prop.latitude<=90 and -180<=prop.longitude<=180): abort(400,'Coordenadas fuera de rango')
    if prop.price<0 or min(prop.bedrooms,prop.bathrooms,prop.area)<0: abort(400,'Valores negativos')
    prop.status=request.form.get('status','disponible')
    if prop.status not in ('disponible','reservada','vendida'): abort(400,'Estado inválido')

@app.route('/')
def index():
    q=request.args.get('q','').strip()[:100]
    city=request.args.get('city','').strip()[:100]
    max_price=request.args.get('max_price','',type=int)
    query=Property.query.filter_by(status='disponible')
    if q: query=query.filter(or_(Property.title.ilike(f'%{q}%'),Property.description.ilike(f'%{q}%')))
    if city: query=query.filter(Property.city.ilike(f'%{city}%'))
    if max_price and max_price>0: query=query.filter(Property.price<=max_price)
    return render_template('index.html',properties=query.order_by(Property.created_at.desc()).all(),q=q,city=city,max_price=max_price)

@app.route('/propiedad/<int:id>')
def detail(id):
    prop=db.get_or_404(Property,id)
    if prop.status!='disponible' and not session.get('admin_id'): abort(404)
    return render_template('detail.html',p=prop)

@app.post('/propiedad/<int:id>/interes')
def interest(id):
    prop=db.get_or_404(Property,id)
    if prop.status!='disponible': abort(404)
    name=request.form.get('name','').strip()[:140]
    email=request.form.get('email','').strip()[:180]
    phone=request.form.get('phone','').strip()[:40]
    level=request.form.get('interest','medio')
    if not name or '@' not in email or not phone or level not in ('alto','medio','bajo') or request.form.get('consent') != 'yes': abort(400,'Datos incompletos o autorización faltante')
    date_str=request.form.get('preferred_date','')
    try: preferred=datetime.strptime(date_str,'%Y-%m-%d').date() if date_str else None
    except ValueError: abort(400,'Fecha inválida')
    budget=integer('budget') if request.form.get('budget') else None
    if budget is not None and budget<0: abort(400,'Presupuesto inválido')
    db.session.add(Lead(property_id=id,name=name,email=email,phone=phone,interest=level,budget=budget,message=request.form.get('message','')[:2000],preferred_date=preferred))
    db.session.commit()
    flash('¡Solicitud enviada! Un asesor se pondrá en contacto contigo.','success')
    return redirect(url_for('detail',id=id))

@app.route('/admin/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        admin=Admin.query.filter_by(email=request.form.get('email','').strip().lower()).first()
        if admin and check_password_hash(admin.password_hash,request.form.get('password','')):
            session.clear();session['admin_id']=admin.id
            return redirect(url_for('dashboard'))
        flash('Credenciales incorrectas','error')
    return render_template('login.html')

@app.post('/admin/logout')
@admin_required
def logout(): session.clear();return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def dashboard():
    return render_template('admin.html',properties=Property.query.order_by(Property.id.desc()).all(),leads=Lead.query.order_by(Lead.id.desc()).all(),appointments=Appointment.query.order_by(Appointment.scheduled_at.desc()).all())

@app.route('/admin/propiedad/nueva',methods=['GET','POST'])
@app.route('/admin/propiedad/<int:id>/editar',methods=['GET','POST'])
@admin_required
def property_form(id=None):
    prop=db.get_or_404(Property,id) if id else None
    if request.method=='POST':
        if prop is None: prop=Property();db.session.add(prop)
        fill_property(prop)
        save_photos(prop)
        db.session.commit()
        flash('Propiedad guardada correctamente','success')
        return redirect(url_for('dashboard'))
    return render_template('property_form.html',p=prop)

@app.post('/admin/propiedad/<int:id>/eliminar')
@admin_required
def delete_property(id):
    prop=db.get_or_404(Property,id)
    # Conservar los interesados y las citas; retirar la vivienda del catálogo.
    prop.status='vendida'
    db.session.commit()
    flash('Propiedad retirada del catálogo; historial conservado','success')
    return redirect(url_for('dashboard'))

@app.post('/admin/foto/<int:id>/eliminar')
@admin_required
def delete_photo(id):
    photo=db.get_or_404(Photo,id)
    pid=photo.property_id
    filepath=Path(app.config['UPLOAD_FOLDER'])/photo.filename
    db.session.delete(photo);db.session.commit()
    filepath.unlink(missing_ok=True)
    return redirect(url_for('property_form',id=pid))

@app.post('/admin/cita')
@admin_required
def create_appointment():
    lead=db.get_or_404(Lead,integer('lead_id'))
    try: scheduled=datetime.strptime(request.form['scheduled_at'],'%Y-%m-%dT%H:%M')
    except ValueError: abort(400,'Fecha inválida')
    if scheduled<=datetime.now(): abort(400,'La cita debe ser futura')
    collision=Appointment.query.filter_by(scheduled_at=scheduled,status='confirmada').first()
    if collision: flash('Ya hay una cita confirmada en esa fecha y hora','error');return redirect(url_for('dashboard'))
    db.session.add(Appointment(lead_id=lead.id,scheduled_at=scheduled,notes=request.form.get('notes','')[:1000]))
    db.session.commit()
    flash('Cita programada','success')
    return redirect(url_for('dashboard'))

@app.post('/admin/cita/<int:id>/estado')
@admin_required
def appointment_status(id):
    ap=db.get_or_404(Appointment,id)
    status=request.form.get('status')
    if status not in ('confirmada','completada','cancelada'): abort(400)
    ap.status=status;db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/health')
def health(): return jsonify(status='ok')

@app.cli.command('init-db')
def init_db():
    db.create_all()
    email=os.environ.get('ADMIN_EMAIL','').strip().lower()
    password=os.environ.get('ADMIN_PASSWORD','')
    if not email or len(password)<12: raise RuntimeError('Configura ADMIN_EMAIL y ADMIN_PASSWORD (mínimo 12 caracteres)')
    if not Admin.query.filter_by(email=email).first():
        db.session.add(Admin(email=email,password_hash=generate_password_hash(password)))
        db.session.commit()
    print('Base de datos y administrador preparados')

if __name__=='__main__': app.run(debug=os.environ.get('FLASK_DEBUG')=='1')
