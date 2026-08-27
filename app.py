from flask import (Flask, render_template, request, redirect, url_for, flash,
                   send_from_directory, jsonify, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text
import hashlib
import io
import logging
import os
import re
import uuid
from datetime import datetime

app = Flask(__name__,
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-insecure-key-change-me')


def database_uri():
    """Prefer a hosted database; fall back to local SQLite for development.

    Serverless hosts (Vercel and similar) serve the deployment from a
    read-only filesystem, so writing to a bundled SQLite file raises
    "attempt to write a readonly database" on every INSERT -- registration,
    listing a product and placing an order all fail. Set DATABASE_URL to a
    hosted Postgres instance in that environment.
    """
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        return 'sqlite:///marketplace.db'
    # Heroku/Neon/Supabase hand out the legacy postgres:// scheme, which
    # SQLAlchemy 1.4+ no longer registers.
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


app.config['SQLALCHEMY_DATABASE_URI'] = database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
    # Serverless instances are recycled freely, so connections go stale
    # between invocations; check them out before use and recycle often.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

logging.basicConfig(level=logging.INFO)

# Ensure upload directory exists. Serverless hosts mount the deployment
# read-only, so this must never crash the app at import time.
UPLOAD_FOLDER = os.path.join('static', 'uploads')
UPLOAD_PATH = os.path.join(app.root_path, UPLOAD_FOLDER)
try:
    os.makedirs(UPLOAD_PATH, exist_ok=True)
except OSError:
    pass
app.config['UPLOAD_FOLDER'] = UPLOAD_PATH

# Ensure default images directory exists
DEFAULT_IMAGES_PATH = os.path.join(app.root_path, 'static', 'images', 'default')
try:
    os.makedirs(DEFAULT_IMAGES_PATH, exist_ok=True)
except OSError:
    pass

# Pictures for the seasonal cards on the home page
SEASONAL_IMAGES_PATH = os.path.join(app.root_path, 'static', 'images', 'seasonal')

MAX_UPLOAD_MB = 16
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024  # max file size
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

# The categories a farmer can pick from
CATEGORIES = ['Vegetables', 'Fruits', 'Grains', 'Dairy', 'Other']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_category(raw):
    """Keep categories consistent so 'vegetables' and 'Vegetables' don't split apart."""
    value = (raw or '').strip()
    for known in CATEGORIES:
        if value.lower() == known.lower():
            return known
    return value.title() if value else 'Other'


def slugify(value):
    """'Green Peas' -> 'green-peas' (used to find a seasonal item's picture)."""
    return re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')


class UploadError(Exception):
    """Raised when a picture cannot be stored; the product itself still saves."""


def seasonal_image(name):
    """Picture for one seasonal item.

    Order of preference:
      1. a real photo dropped into static/images/seasonal/<slug>.jpg|jpeg|png|webp
      2. the drawing from create_seasonal_images.py (<slug>.svg)
      3. the generated placeholder in static/images/default/<slug_with_underscores>.jpg
      4. None, so the caller falls back to the generic category image
    """
    slug = slugify(name)
    for ext in ('jpg', 'jpeg', 'png', 'webp', 'svg'):
        candidate = '{}.{}'.format(slug, ext)
        if os.path.exists(os.path.join(SEASONAL_IMAGES_PATH, candidate)):
            return 'images/seasonal/' + candidate
    legacy = '{}.jpg'.format(slug.replace('-', '_'))
    if os.path.exists(os.path.join(DEFAULT_IMAGES_PATH, legacy)):
        return 'images/default/' + legacy
    return None


# Photos are re-encoded to this size before being stored, so a 12 MP phone
# picture becomes a ~200 KB JPEG instead of filling up the database.
IMAGE_MAX_EDGE = 1200
IMAGE_QUALITY = 82


def process_image(raw_bytes):
    """Shrink and re-encode an uploaded photo. Returns (bytes, mimetype).

    Falls back to the original bytes if Pillow is unavailable or cannot read
    the file - a slightly large picture is better than no picture.
    """
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(raw_bytes))
        img = ImageOps.exif_transpose(img)          # honour phone rotation
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        img.thumbnail((IMAGE_MAX_EDGE, IMAGE_MAX_EDGE), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
        return out.getvalue(), 'image/jpeg'
    except Exception as e:
        app.logger.warning('Could not re-encode upload, storing as-is: %s', e)
        return raw_bytes, 'image/jpeg'


def store_product_image(product_id, file_storage):
    """Save an uploaded photo for a product. Returns True if one was stored.

    Raises UploadError for a file type we cannot use. Nothing is written to
    disk, so this works the same locally and on a read-only serverless host.
    """
    if not file_storage or not file_storage.filename:
        return False
    if not allowed_file(file_storage.filename):
        raise UploadError(
            'Saved without a photo: that image type is not supported. Please '
            'edit the product and upload a '
            + ', '.join(sorted(ALLOWED_EXTENSIONS)) + ' file.')

    raw = file_storage.read()
    if not raw:
        return False

    data, mimetype = process_image(raw)
    row = ProductImage.query.get(product_id)
    if row is None:
        row = ProductImage(product_id=product_id)
        db.session.add(row)
    row.data = data
    row.mimetype = mimetype
    row.etag = hashlib.md5(data).hexdigest()
    row.updated_at = datetime.utcnow()
    return True


def drop_product_image(product_id):
    """Remove a product's stored photo, if it has one."""
    ProductImage.query.filter_by(product_id=product_id).delete(synchronize_session=False)


def delete_image(image_url, keep_product_id=None):
    """Remove a stored product image from disk, ignoring failures.

    Skips the delete when another product still points at the same file, so
    removing one listing can never blank out somebody else's picture.
    """
    if not image_url or not image_url.startswith('uploads/'):
        return
    try:
        others = Product.query.filter(Product.image_url == image_url)
        if keep_product_id is not None:
            others = others.filter(Product.id != keep_product_id)
        if others.count() > 0:
            return
    except Exception:
        pass
    image_path = os.path.join(app.root_path, 'static', image_url.lstrip('/'))
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
    except OSError as e:
        app.logger.warning('Error deleting image file: %s', e)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_farmer = db.Column(db.Boolean, default=False)
    # Address fields
    street_address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(6))
    phone = db.Column(db.String(10))
    products = db.relationship('Product', backref='seller', lazy=True)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)

    def get_id(self):
        return str(self.id)

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')
    # Add delivery address fields
    delivery_street = db.Column(db.String(200))
    delivery_city = db.Column(db.String(100))
    delivery_state = db.Column(db.String(100))
    delivery_pincode = db.Column(db.String(6))
    delivery_phone = db.Column(db.String(10))
    product = db.relationship('Product', backref='orders')
    buyer = db.relationship('User', backref='purchases')

    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'

class ProductImage(db.Model):
    """A product photo, stored in the database rather than on disk.

    Vercel (and every other serverless host) serves the app from a read-only
    filesystem, so a photo written into static/uploads/ is lost the moment the
    request ends - the picture simply never appeared on the site. Keeping the
    bytes in the same database as everything else means an uploaded photo
    survives, works across every instance, and needs no extra service.
    """
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), primary_key=True)
    data = db.Column(db.LargeBinary, nullable=False)
    mimetype = db.Column(db.String(60), nullable=False, default='image/jpeg')
    etag = db.Column(db.String(32), nullable=False, default='')
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    # Get current month to determine season
    current_month = datetime.now().month
    
    # Define seasonal recommendations
    seasonal_info = {
        'winter': {
            'months': [11, 12, 1, 2],
            'vegetables': [
                {'name': 'Carrots', 'benefits': 'Rich in vitamin A, good for eye health', 'image': 'default/carrots.jpg'},
                {'name': 'Spinach', 'benefits': 'High in iron and vitamins', 'image': 'default/spinach.jpg'},
                {'name': 'Cauliflower', 'benefits': 'Low in calories, high in fiber', 'image': 'default/cauliflower.jpg'},
                {'name': 'Green Peas', 'benefits': 'Good source of protein and fiber', 'image': 'default/green_peas.jpg'}
            ],
            'fruits': [
                {'name': 'Oranges', 'benefits': 'High in vitamin C, boosts immunity', 'image': 'default/oranges.jpg'},
                {'name': 'Apples', 'benefits': 'Rich in antioxidants', 'image': 'default/apples.jpg'},
                {'name': 'Guava', 'benefits': 'High in vitamin C and fiber', 'image': 'default/guava.jpg'}
            ]
        },
        'summer': {
            'months': [3, 4, 5, 6],
            'vegetables': [
                {'name': 'Cucumber', 'benefits': 'Hydrating and cooling', 'image': 'default/cucumber.jpg'},
                {'name': 'Tomatoes', 'benefits': 'Rich in lycopene, good for heart', 'image': 'default/tomatoes.jpg'},
                {'name': 'Bottle Gourd', 'benefits': 'Cooling effect, good for digestion', 'image': 'default/bottle_gourd.jpg'}
            ],
            'fruits': [
                {'name': 'Mangoes', 'benefits': 'Rich in vitamins A and C', 'image': 'default/mangoes.jpg'},
                {'name': 'Watermelon', 'benefits': 'Hydrating, rich in antioxidants', 'image': 'default/watermelon.jpg'},
                {'name': 'Lychee', 'benefits': 'Good source of vitamin C', 'image': 'default/lychee.jpg'}
            ]
        },
        'monsoon': {
            'months': [7, 8, 9, 10],
            'vegetables': [
                {'name': 'Bitter Gourd', 'benefits': 'Boosts immunity, good for diabetes', 'image': 'default/bitter_gourd.jpg'},
                {'name': 'Lady Finger', 'benefits': 'Rich in fiber and minerals', 'image': 'default/lady_finger.jpg'},
                {'name': 'Corn', 'benefits': 'Good source of energy', 'image': 'default/corn.jpg'}
            ],
            'fruits': [
                {'name': 'Pomegranate', 'benefits': 'Rich in antioxidants', 'image': 'default/pomegranate.jpg'},
                {'name': 'Pear', 'benefits': 'Good for digestion', 'image': 'default/pear.jpg'},
                {'name': 'Jamun', 'benefits': 'Good for diabetics', 'image': 'default/jamun.jpg'}
            ]
        }
    }
    
    # Determine current season
    if current_month in seasonal_info['winter']['months']:
        current_season = 'winter'
    elif current_month in seasonal_info['summer']['months']:
        current_season = 'summer'
    else:
        current_season = 'monsoon'
    
    season_data = seasonal_info[current_season]

    # Attach a picture to every seasonal item (falls back to the category image)
    for kind, fallback in (('vegetables', 'images/default/vegetables.jpg'),
                           ('fruits', 'images/default/fruits.jpg')):
        for item in season_data[kind]:
            item['slug'] = slugify(item['name'])
            item['image'] = seasonal_image(item['name']) or fallback
            item['fallback'] = fallback
    
    # Get search parameters
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    
    # Query products with search filters
    products_query = Product.query
    
    if search_query:
        search_filter = (
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.description.ilike(f'%{search_query}%'))
        )
        products_query = products_query.filter(search_filter)
    
    if category_filter:
        # match case-insensitively so older lowercase rows still show up
        products_query = products_query.filter(Product.category.ilike(category_filter))
    
    # Get unique categories for the filter dropdown
    categories = db.session.query(Product.category).distinct().all()
    categories = sorted({normalize_category(c[0]) for c in categories if c[0]})
    
    products = products_query.all()
    
    return render_template('index.html', 
                         season=current_season,
                         seasonal_data=season_data,
                         products=products,
                         categories=categories,
                         search_query=search_query,
                         category_filter=category_filter)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            is_farmer = 'is_farmer' in request.form
            
            # Check if username or email already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'danger')
                return redirect(url_for('register'))
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'danger')
                return redirect(url_for('register'))
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_farmer=is_farmer
            )
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            app.logger.exception('Registration failed')
            flash('An error occurred during registration', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            user = User.query.filter_by(username=request.form['username']).first()
            if user and check_password_hash(user.password_hash, request.form['password']):
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('home'))
            flash('Invalid username or password', 'danger')
        except Exception:
            app.logger.exception('Login failed')
            flash('An error occurred during login', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/product_image/<int:product_id>')
def product_image(product_id):
    """Serve a product photo.

    One URL covers every case, so templates never have to guess:
      1. the photo stored in the database (what new uploads use)
      2. a legacy file still sitting in static/uploads/ from a local run
      3. otherwise a redirect to the category placeholder
    """
    row = ProductImage.query.get(product_id)
    if row is not None and row.data:
        if request.headers.get('If-None-Match') == row.etag:
            return Response(status=304)
        response = Response(row.data, mimetype=row.mimetype)
        response.headers['Cache-Control'] = 'public, max-age=300'
        response.headers['ETag'] = row.etag
        return response

    product = Product.query.get(product_id)
    if product is not None and product.image_url:
        legacy = os.path.join(app.root_path, 'static', *product.image_url.split('/'))
        if os.path.exists(legacy):
            return redirect(url_for('static', filename=product.image_url))

    category = (product.category or '').lower() if product else ''
    placeholder = 'images/default/fruits.jpg' if category == 'fruits' else 'images/default/vegetables.jpg'
    return redirect(url_for('static', filename=placeholder))


@app.route('/my_products')
@login_required
def my_products():
    """A farmer's own listings, with Edit and Delete on every card."""
    if not current_user.is_farmer:
        flash('Only farmers have a product list', 'danger')
        return redirect(url_for('home'))

    products = (Product.query
                .filter_by(seller_id=current_user.id)
                .order_by(Product.id.desc())
                .all())
    return render_template('my_products.html', products=products)


@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_farmer:
        flash('Only farmers can add products', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Keep what was typed so a failed submit never wipes the form
        form = {
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'price': request.form.get('price', '').strip(),
            'quantity': request.form.get('quantity', '').strip(),
            'category': request.form.get('category', '').strip(),
        }
        try:
            if not form['name']:
                raise ValueError('Please enter a product name.')
            if not form['category']:
                raise ValueError('Please choose a category.')
            category = normalize_category(form['category'])
            try:
                price = float(form['price'])
            except (TypeError, ValueError):
                raise ValueError('Please enter a valid price.')
            try:
                quantity = int(form['quantity'])
            except (TypeError, ValueError):
                raise ValueError('Please enter a valid quantity.')
            if price < 0 or quantity < 0:
                raise ValueError('Price and quantity cannot be negative.')

            # Listing several products in one category is fine. If it is
            # literally the same item, say so instead of silently creating a
            # duplicate the farmer has to clean up later.
            existing = (Product.query
                        .filter_by(seller_id=current_user.id)
                        .filter(Product.name.ilike(form['name']))
                        .filter(Product.category.ilike(category))
                        .first())

            product = Product(
                name=form['name'],
                description=form['description'],
                price=price,
                quantity=quantity,
                category=category,
                image_url='',
                seller_id=current_user.id
            )
            db.session.add(product)
            db.session.flush()          # assigns product.id for the photo row

            upload_warning = None
            try:
                store_product_image(product.id, request.files.get('image'))
            except UploadError as e:
                upload_warning = str(e)

            db.session.commit()

            if upload_warning:
                flash(upload_warning, 'warning')
            if existing:
                flash('Added. Heads up: you already had "{}" listed under {} - '
                      'you can merge or remove the older one from My Products.'
                      .format(existing.name, existing.category), 'warning')
            flash('Product added successfully!', 'success')
            return redirect(url_for('my_products'))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return render_template('add_product.html', categories=CATEGORIES, form=form)
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Adding product failed')
            flash('Could not add the product: {}'.format(e), 'danger')
            return render_template('add_product.html', categories=CATEGORIES, form=form)

    return render_template('add_product.html', categories=CATEGORIES, form={})

@app.route('/buy_product/<int:product_id>', methods=['POST'])
@login_required
def buy_product(product_id):
    if current_user.is_farmer:
        flash('Farmers cannot buy products', 'danger')
        return redirect(url_for('home'))
    
    if not current_user.street_address or not current_user.phone:
        flash('Please update your profile with delivery address before making a purchase', 'warning')
        return redirect(url_for('profile'))
    
    try:
        product = Product.query.get_or_404(product_id)
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            flash('Please enter a valid quantity', 'danger')
            return redirect(url_for('home'))
        
        if quantity > product.quantity:
            flash('Not enough stock available', 'danger')
            return redirect(url_for('home'))
        
        total_price = product.price * quantity
        
        # Create order with delivery address
        order = Order(
            product_id=product.id,
            buyer_id=current_user.id,
            quantity=quantity,
            total_price=total_price,
            delivery_street=current_user.street_address,
            delivery_city=current_user.city,
            delivery_state=current_user.state,
            delivery_pincode=current_user.pincode,
            delivery_phone=current_user.phone
        )
        
        # Update product quantity
        product.quantity -= quantity
        
        db.session.add(order)
        db.session.commit()
        
        flash(f'Successfully ordered {quantity} {product.name}(s)', 'success')
        return redirect(url_for('my_orders'))
    except Exception:
        db.session.rollback()
        app.logger.exception('Order processing failed')
        flash('An error occurred while processing your order', 'danger')
        return redirect(url_for('home'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_farmer:
        flash('Only farmers can delete products', 'danger')
        return redirect(url_for('home'))

    product = Product.query.get_or_404(product_id)

    if product.seller_id != current_user.id:
        flash('You can only delete your own products', 'danger')
        return redirect(url_for('my_products'))

    # Read what we need BEFORE the row leaves the session
    image_url = product.image_url
    name = product.name

    try:
        # Clear rows in other tables that point at this product, or Postgres
        # refuses the delete on a foreign key.
        #
        # cart_item only exists in older SQLite databases, so its absence must
        # not abort the transaction. On Postgres any failed statement poisons
        # the whole transaction, so this runs inside a SAVEPOINT: if the table
        # is missing, only the savepoint rolls back and the deletes below still
        # go through.
        try:
            with db.session.begin_nested():
                db.session.execute(
                    text('DELETE FROM cart_item WHERE product_id = :pid'), {'pid': product.id})
        except Exception:
            app.logger.info('No cart_item table to clean up; continuing')

        drop_product_image(product.id)
        Order.query.filter_by(product_id=product.id).delete(synchronize_session=False)
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Deleting product failed')
        flash('Could not delete the product: {}'.format(e), 'danger')
        return redirect(url_for('my_products'))

    # Only now touch the file on disk, and only if nothing else uses it
    delete_image(image_url)

    flash('"{}" was deleted'.format(name), 'success')
    return redirect(url_for('my_products'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if not current_user.is_farmer:
        flash('Only farmers can edit products', 'danger')
        return redirect(url_for('home'))

    product = Product.query.get_or_404(product_id)

    if product.seller_id != current_user.id:
        flash('You can only edit your own products', 'danger')
        return redirect(url_for('my_products'))

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            category = normalize_category(request.form.get('category', ''))

            if not name:
                raise ValueError('Please enter a product name.')
            try:
                price = float(request.form.get('price', ''))
            except (TypeError, ValueError):
                raise ValueError('Please enter a valid price.')
            try:
                quantity = int(request.form.get('quantity', ''))
            except (TypeError, ValueError):
                raise ValueError('Please enter a valid quantity.')
            if price < 0 or quantity < 0:
                raise ValueError('Price and quantity cannot be negative.')

            old_image = product.image_url
            upload_warning = None
            replaced = False
            try:
                replaced = store_product_image(product.id, request.files.get('image'))
            except UploadError as e:
                upload_warning = str(e)

            if replaced:
                product.image_url = ''      # the database copy is the photo now
            elif 'remove_image' in request.form:
                drop_product_image(product.id)
                product.image_url = ''

            product.name = name
            product.description = description
            product.price = price
            product.quantity = quantity
            product.category = category

            db.session.commit()

            # A legacy file on disk goes only once the new value is saved
            if old_image and old_image != product.image_url:
                delete_image(old_image, keep_product_id=product.id)

            if upload_warning:
                flash(upload_warning, 'warning')
            flash('Product updated successfully!', 'success')
            return redirect(url_for('my_products'))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return render_template('edit_product.html', product=product, categories=CATEGORIES)
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Updating product failed')
            flash('Could not update the product: {}'.format(e), 'danger')
            return render_template('edit_product.html', product=product, categories=CATEGORIES)

    return render_template('edit_product.html', product=product, categories=CATEGORIES)

@app.route('/update_order_status/<int:order_id>/<string:status>', methods=['POST'])
@login_required
def update_order_status(order_id, status):
    if not current_user.is_farmer:
        flash('Only farmers can update order status', 'danger')
        return redirect(url_for('my_orders'))
    
    order = Order.query.get_or_404(order_id)
    
    # Verify the order belongs to one of the farmer's products
    product = Product.query.get(order.product_id)
    if product.seller_id != current_user.id:
        flash('You can only update status for your own products', 'danger')
        return redirect(url_for('my_orders'))
    
    # Validate status
    valid_statuses = [Order.STATUS_ACCEPTED, Order.STATUS_REJECTED, Order.STATUS_COMPLETED]
    if status not in valid_statuses:
        flash('Invalid status', 'danger')
        return redirect(url_for('my_orders'))

    # Capture the previous status BEFORE mutating the order, otherwise the
    # stock adjustments below compare the new status against itself and
    # never run.
    previous_status = order.status

    if previous_status == status:
        flash(f'Order is already {status}')
        return redirect(url_for('my_orders'))

    try:
        # If rejecting a previously non-rejected order, return the reserved
        # stock to the product.
        if status == Order.STATUS_REJECTED and previous_status != Order.STATUS_REJECTED:
            product.quantity += order.quantity

        # If accepting a previously rejected order, reserve the stock again.
        if status == Order.STATUS_ACCEPTED and previous_status == Order.STATUS_REJECTED:
            if product.quantity < order.quantity:
                flash('Not enough quantity available', 'danger')
                return redirect(url_for('my_orders'))
            product.quantity -= order.quantity

        order.status = status

        db.session.commit()
        flash(f'Order status updated to {status}', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Order status update failed')
        flash('Error updating order status', 'danger')
        
    return redirect(url_for('my_orders'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            current_user.phone = request.form['phone']
            current_user.street_address = request.form['street_address']
            current_user.city = request.form['city']
            current_user.state = request.form['state']
            current_user.pincode = request.form['pincode']
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception:
            db.session.rollback()
            app.logger.exception('Updating profile failed')
            flash('An error occurred while updating your profile', 'danger')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/my_orders')
@login_required
def my_orders():
    if current_user.is_farmer:
        # Show orders for farmer's products
        products = Product.query.filter_by(seller_id=current_user.id).all()
        product_ids = [p.id for p in products]
        orders = Order.query.filter(Order.product_id.in_(product_ids)).all()
    else:
        # Show customer's orders
        orders = Order.query.filter_by(buyer_id=current_user.id).all()
    
    return render_template('my_order.html', orders=orders)

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    # silent=True keeps a malformed or non-JSON body from raising a 400 that
    # the chat widget cannot parse.
    payload = request.get_json(silent=True) or {}
    message = str(payload.get('message', '')).lower()

    if not message.strip():
        return jsonify({'response': 'Please type a message so I can help.'}), 400


    # Basic response logic based on user type and message content
    responses = {
        'farmer': {
            'product': 'To add or manage products, use the "Add Product" button in the navigation menu.',
            'order': 'You can view and manage your sales in the "My Sales" section.',
            'price': 'Set competitive prices based on market rates and your production costs.',
            'delivery': 'Ensure your products are properly packed and ready for delivery when orders are received.'
        },
        'customer': {
            'product': 'Browse our fresh products on the home page. Click on any product to view details.',
            'order': 'Track your orders in the "My Orders" section after logging in.',
            'price': 'Our prices are set directly by farmers to ensure fair rates.',
            'delivery': 'Delivery details will be provided once your order is confirmed.'
        },
        'general': {
            'help': 'How can I assist you today? Ask me about products, orders, or general information.',
            'contact': 'You can reach us at agromarket@gmail.com or call +1 (555) 123-4567.',
            'about': 'We are a platform connecting farmers directly with customers for fresh produce.'
        }
    }
    
    # Determine user type and appropriate response
    user_type = 'farmer' if current_user.is_farmer else 'customer'
    
    # Find the most relevant response
    response = None
    if 'help' in message:
        response = responses['general']['help']
    elif 'contact' in message:
        response = responses['general']['contact']
    elif 'about' in message:
        response = responses['general']['about']
    elif any(key in message for key in ['product', 'order', 'price', 'delivery']):
        for key in ['product', 'order', 'price', 'delivery']:
            if key in message:
                response = responses[user_type][key]
                break
    
    if not response:
        response = "I'm not sure about that. Please ask about products, orders, pricing, or delivery."
    
    # Save the chat message
    chat_message = ChatMessage(
        user_id=current_user.id,
        message=message,
        response=response
    )
    db.session.add(chat_message)
    db.session.commit()
    
    return jsonify({'response': response})

@app.errorhandler(413)
def file_too_large(error):
    flash('That image is too large. Please upload a picture under {} MB.'.format(MAX_UPLOAD_MB),
          'danger')
    return redirect(request.referrer or url_for('add_product')), 302

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', error_code=500, error_message="Something went wrong on our end"), 500

# Create the schema at import time, not only under __main__.
# Under gunicorn ("web: gunicorn app:app") the __main__ block never executes,
# so without this every request failed with "no such table: product".
#
# A database that is unreachable at import time must not take the whole
# process down: on a serverless host that would turn a transient blip during a
# cold start into a hard 500 for every route, including the pages that do not
# touch the database. Log it and let individual requests fail instead.
with app.app_context():
    try:
        db.create_all()
    except Exception:
        app.logger.exception(
            'Could not create database schema at startup. '
            'Check DATABASE_URL; the app will keep serving read-only pages.'
        )


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)