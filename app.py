from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

app = Flask(__name__, 
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-insecure-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///marketplace.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join('static', 'uploads')
UPLOAD_PATH = os.path.join(app.root_path, UPLOAD_FOLDER)
os.makedirs(UPLOAD_PATH, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_PATH

# Ensure default images directory exists
DEFAULT_IMAGES_PATH = os.path.join(app.root_path, 'static', 'images', 'default')
os.makedirs(DEFAULT_IMAGES_PATH, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    """Save an uploaded image under a collision-free name.

    secure_filename() alone is not unique: two sellers uploading 'tomato.jpg'
    would silently overwrite each other's picture. Prefixing a random token
    keeps every upload distinct.
    """
    filename = secure_filename(file.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
    return 'uploads/' + unique_name


def delete_image(image_url):
    """Remove a stored product image from disk, ignoring failures."""
    if not image_url:
        return
    image_path = os.path.join(app.root_path, 'static', image_url.lstrip('/'))
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
    except OSError as e:
        print(f"Error deleting image file: {e}")

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
                {'name': 'Carrots', 'benefits': 'Rich in vitamin A, good for eye health', 'image': 'default/vegetables.jpg'},
                {'name': 'Spinach', 'benefits': 'High in iron and vitamins', 'image': 'default/vegetables.jpg'},
                {'name': 'Cauliflower', 'benefits': 'Low in calories, high in fiber', 'image': 'default/vegetables.jpg'},
                {'name': 'Green Peas', 'benefits': 'Good source of protein and fiber', 'image': 'default/vegetables.jpg'}
            ],
            'fruits': [
                {'name': 'Oranges', 'benefits': 'High in vitamin C, boosts immunity', 'image': 'default/fruits.jpg'},
                {'name': 'Apples', 'benefits': 'Rich in antioxidants', 'image': 'default/fruits.jpg'},
                {'name': 'Guava', 'benefits': 'High in vitamin C and fiber', 'image': 'default/fruits.jpg'}
            ]
        },
        'summer': {
            'months': [3, 4, 5, 6],
            'vegetables': [
                {'name': 'Cucumber', 'benefits': 'Hydrating and cooling', 'image': 'default/vegetables.jpg'},
                {'name': 'Tomatoes', 'benefits': 'Rich in lycopene, good for heart', 'image': 'default/vegetables.jpg'},
                {'name': 'Bottle Gourd', 'benefits': 'Cooling effect, good for digestion', 'image': 'default/vegetables.jpg'}
            ],
            'fruits': [
                {'name': 'Mangoes', 'benefits': 'Rich in vitamins A and C', 'image': 'default/fruits.jpg'},
                {'name': 'Watermelon', 'benefits': 'Hydrating, rich in antioxidants', 'image': 'default/fruits.jpg'},
                {'name': 'Lychee', 'benefits': 'Good source of vitamin C', 'image': 'default/fruits.jpg'}
            ]
        },
        'monsoon': {
            'months': [7, 8, 9, 10],
            'vegetables': [
                {'name': 'Bitter Gourd', 'benefits': 'Boosts immunity, good for diabetes', 'image': 'default/vegetables.jpg'},
                {'name': 'Lady Finger', 'benefits': 'Rich in fiber and minerals', 'image': 'default/vegetables.jpg'},
                {'name': 'Corn', 'benefits': 'Good source of energy', 'image': 'default/vegetables.jpg'}
            ],
            'fruits': [
                {'name': 'Pomegranate', 'benefits': 'Rich in antioxidants', 'image': 'default/fruits.jpg'},
                {'name': 'Pear', 'benefits': 'Good for digestion', 'image': 'default/fruits.jpg'},
                {'name': 'Jamun', 'benefits': 'Good for diabetics', 'image': 'default/fruits.jpg'}
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
        products_query = products_query.filter(Product.category == category_filter)
    
    # Get unique categories for the filter dropdown
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
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
                flash('Username already exists')
                return redirect(url_for('register'))
            if User.query.filter_by(email=email).first():
                flash('Email already exists')
                return redirect(url_for('register'))
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_farmer=is_farmer
            )
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            user = User.query.filter_by(username=request.form['username']).first()
            if user and check_password_hash(user.password_hash, request.form['password']):
                login_user(user)
                flash('Logged in successfully!')
                return redirect(url_for('home'))
            flash('Invalid username or password')
        except Exception as e:
            flash('An error occurred during login')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('home'))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_farmer:
        flash('Only farmers can add products')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        try:
            # Handle file upload
            image_url = ''
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # Store the URL path relative to static directory
                    image_url = save_upload(file)

            product = Product(
                name=request.form['name'],
                description=request.form['description'],
                price=float(request.form['price']),
                quantity=int(request.form['quantity']),
                category=request.form['category'],
                image_url=image_url,
                seller_id=current_user.id
            )
            db.session.add(product)
            db.session.commit()
            flash('Product added successfully!')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            print(f"Error adding product: {e}")  # For debugging
            flash('An error occurred while adding the product')
            return redirect(url_for('add_product'))
    return render_template('add_product.html')

@app.route('/buy_product/<int:product_id>', methods=['POST'])
@login_required
def buy_product(product_id):
    if current_user.is_farmer:
        flash('Farmers cannot buy products')
        return redirect(url_for('home'))
    
    if not current_user.street_address or not current_user.phone:
        flash('Please update your profile with delivery address before making a purchase')
        return redirect(url_for('profile'))
    
    try:
        product = Product.query.get_or_404(product_id)
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            flash('Please enter a valid quantity')
            return redirect(url_for('home'))
        
        if quantity > product.quantity:
            flash('Not enough stock available')
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
        
        flash(f'Successfully ordered {quantity} {product.name}(s)')
        return redirect(url_for('my_orders'))
    except Exception as e:
        db.session.rollback()
        print(f"Error processing order: {e}")
        flash('An error occurred while processing your order')
        return redirect(url_for('home'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_farmer:
        flash('Only farmers can delete products')
        return redirect(url_for('home'))
    
    try:
        product = Product.query.get_or_404(product_id)

        if product.seller_id != current_user.id:
            flash('You can only delete your own products')
            return redirect(url_for('home'))

        # Read the image path BEFORE the row is deleted from the session.
        image_url = product.image_url

        # First delete associated orders
        Order.query.filter_by(product_id=product.id).delete()

        # Then delete the product
        db.session.delete(product)

        db.session.commit()

        # Only remove the file once the database change actually succeeded,
        # so a rollback can never leave a product row pointing at a missing image.
        delete_image(image_url)
        flash('Product deleted successfully')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting product: {e}")  # For debugging
        flash('An error occurred while deleting the product')
        return redirect(url_for('home'))

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if not current_user.is_farmer:
        flash('Only farmers can edit products')
        return redirect(url_for('home'))
    
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        flash('You can only edit your own products')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        try:
            # Handle image upload or removal
            if 'remove_image' in request.form and product.image_url:
                delete_image(product.image_url)
                product.image_url = ''

            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # Remove old image if it exists, then save the new one
                    delete_image(product.image_url)
                    product.image_url = save_upload(file)


            # Update other fields
            product.name = request.form['name']
            product.description = request.form['description']
            product.price = float(request.form['price'])
            product.quantity = int(request.form['quantity'])
            product.category = request.form['category']
            
            db.session.commit()
            flash('Product updated successfully!')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            print(f"Error updating product: {e}")
            flash('An error occurred while updating the product')
            return redirect(url_for('edit_product', product_id=product_id))
    
    return render_template('edit_product.html', product=product)

@app.route('/update_order_status/<int:order_id>/<string:status>', methods=['POST'])
@login_required
def update_order_status(order_id, status):
    if not current_user.is_farmer:
        flash('Only farmers can update order status')
        return redirect(url_for('my_orders'))
    
    order = Order.query.get_or_404(order_id)
    
    # Verify the order belongs to one of the farmer's products
    product = Product.query.get(order.product_id)
    if product.seller_id != current_user.id:
        flash('You can only update status for your own products')
        return redirect(url_for('my_orders'))
    
    # Validate status
    valid_statuses = [Order.STATUS_ACCEPTED, Order.STATUS_REJECTED, Order.STATUS_COMPLETED]
    if status not in valid_statuses:
        flash('Invalid status')
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
                flash('Not enough quantity available')
                return redirect(url_for('my_orders'))
            product.quantity -= order.quantity

        order.status = status

        db.session.commit()
        flash(f'Order status updated to {status}')
    except Exception as e:
        db.session.rollback()
        flash('Error updating order status')
        
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
            flash('Profile updated successfully!')
        except Exception as e:
            db.session.rollback()
            print(f"Error updating profile: {e}")
            flash('An error occurred while updating your profile')
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
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)