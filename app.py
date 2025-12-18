import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
import logging
from flask_wtf.csrf import CSRFProtect
from models import db, User, Book, Order, Cart, BookRequest, wishlist_table
from forms import LoginForm, RegisterForm, BookForm, StudentForm
import secrets

load_dotenv()

logging.basicConfig(filename='actions_web.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# csrf = CSRFProtect(app)

# Mail config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# Uploads
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize DB and login
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin = User(name='Admin', email='admin@bookstore.com')
        admin.set_password('admin123')
        admin.role = 'admin'
        db.session.add(admin)
        db.session.commit()
        print('Created default admin -> admin@bookstore.com / admin123')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            logging.info(f'User {user.email} logged in')
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        user = User(name=form.name.data, email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        logging.info(f'New user registered: {user.email}')
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logging.info(f'User {current_user.email} logged out')
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name)
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.profile_pic = filename
        db.session.commit()
        flash('Profile updated', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

# Forgot / Reset Password
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found', 'warning')
            return redirect(url_for('forgot_password'))
        token = s.dumps(email, salt='recover-key')
        reset_url = url_for('reset_password', token=token, _external=True)
        msg = Message('Password Reset', recipients=[email])
        msg.body = f'Click here to reset your password:\n{reset_url}\nThis link expires in 30 minutes.'
        mail.send(msg)
        flash('Password reset email sent!', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='recover-key', max_age=1800)
    except Exception:
        flash('Invalid or expired link', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_pw = request.form['password']
        user = User.query.filter_by(email=email).first()
        user.set_password(new_pw)
        db.session.commit()
        flash('Password updated. You can log in now.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', email=email)

# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Not authorized', 'danger')
        return redirect(url_for('index'))
    books = Book.query.all()
    users = User.query.filter_by(role='student').all()
    orders = Order.query.all()
    pending_requests = BookRequest.query.filter_by(status='pending').count()
    return render_template('admin_dashboard.html', books=books, users=users, orders=orders, pending_requests=pending_requests)

@app.route('/admin/books/new', methods=['GET','POST'])
@login_required
def admin_add_book():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    form = BookForm()
    if form.validate_on_submit():
        b = Book(title=form.title.data, author=form.author.data, genre=form.genre.data or 'General', isbn=form.isbn.data, price=form.price.data or 0.0, total_copies=form.total_copies.data or 1, available_copies=form.total_copies.data or 1)
        db.session.add(b)
        db.session.commit()
        logging.info(f'Admin {current_user.email} added book {b.title}')
        flash('Book added', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_book.html', form=form)

@app.route('/catalog')
@login_required
def catalog():
    q = request.args.get('q','')
    if q:
        books = Book.query.filter(Book.title.ilike(f"%{q}%") | Book.author.ilike(f"%{q}%") | Book.genre.ilike(f"%{q}%")).all()
    else:
        books = Book.query.all()
    return render_template('catalog.html', books=books)

@app.route('/order/<int:book_id>', methods=['POST'])
@login_required
def place_order(book_id):
    if current_user.role != 'student':
        return jsonify({'error':'only students may order'}), 403
    qty = int(request.form.get('qty',1))
    book = Book.query.get_or_404(book_id)
    if book.available_copies < qty:
        flash('Not enough copies available', 'warning')
        return redirect(url_for('catalog'))
    book.available_copies -= qty
    o = Order(user_id=current_user.id, book_id=book.id, quantity=qty, status='pending')
    db.session.add(o)
    db.session.commit()
    logging.info(f'User {current_user.email} placed order {o.id} for {book.title} x{qty}')
    flash('Order placed', 'success')
    return redirect(url_for('catalog'))

@app.route('/wishlist/toggle/<int:book_id>', methods=['POST'])
@login_required
def toggle_wishlist(book_id):
    book = Book.query.get_or_404(book_id)
    if book in current_user.wishlist:
        current_user.wishlist.remove(book)
        db.session.commit()
        flash('Removed from wishlist', 'info')
    else:
        current_user.wishlist.append(book)
        db.session.commit()
        flash('Added to wishlist', 'success')
    return redirect(request.referrer or url_for('catalog'))

@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    # Student-specific overview: orders and cart count
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    # cart_count: sum of quantities in Cart for this user
    cart_count = sum(item.quantity for item in getattr(current_user, 'cart_items', []))
    return render_template('student_dashboard.html', orders=orders, cart_count=cart_count)


@app.route('/student/orders/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
def student_edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Not authorized', 'danger')
        return redirect(url_for('index'))
    if order.status != 'pending':
        flash('Only pending orders can be edited', 'warning')
        return redirect(url_for('student_dashboard'))
    if request.method == 'POST':
        try:
            new_qty = int(request.form.get('quantity', order.quantity))
        except ValueError:
            flash('Invalid quantity', 'warning')
            return redirect(url_for('student_edit_order', order_id=order.id))
        max_allowed = order.book.available_copies + order.quantity
        if new_qty < 1 or new_qty > max_allowed:
            flash('Quantity out of range', 'warning')
            return redirect(url_for('student_edit_order', order_id=order.id))
        # adjust available copies
        order.book.available_copies = max_allowed - new_qty
        order.quantity = new_qty
        db.session.commit()
        flash('Order updated', 'success')
        return redirect(url_for('student_dashboard'))
    return render_template('student_edit_order.html', order=order)


@app.route('/student/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def student_cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Not authorized', 'danger')
        return redirect(url_for('index'))
    if order.status != 'pending':
        flash('Only pending orders can be canceled', 'warning')
        return redirect(url_for('student_dashboard'))
    # return copies and mark canceled
    order.book.available_copies += order.quantity
    order.status = 'canceled'
    db.session.commit()
    flash('Order canceled', 'info')
    return redirect(url_for('student_dashboard'))

@app.route('/admin/orders/<int:order_id>/approve', methods=['POST'])
@login_required
def admin_approve_order(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    order.status = 'approved'
    db.session.commit()
    logging.info(f'Admin {current_user.email} approved order {order.id}')
    flash('Order approved', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def admin_cancel_order(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    order.status = 'canceled'
    # Return the copies to available
    order.book.available_copies += order.quantity
    db.session.commit()
    logging.info(f'Admin {current_user.email} canceled order {order.id}')
    flash('Order canceled', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/students/<int:user_id>/edit', methods=['GET','POST'])
@login_required
def admin_edit_student(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    form = StudentForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()
        logging.info(f'Admin {current_user.email} edited student {user.email}')
        flash('Student updated', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_student.html', form=form, user=user)

@app.route('/admin/students/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_student(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    logging.info(f'Admin {current_user.email} deleted student {user.email}')
    flash('Student deleted', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/books/<int:book_id>/edit', methods=['GET','POST'])
@login_required
def admin_edit_book(book_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    if form.validate_on_submit():
        form.populate_obj(book)
        db.session.commit()
        logging.info(f'Admin {current_user.email} edited book {book.title}')
        flash('Book updated', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_book.html', form=form, book=book)

@app.route('/admin/books/<int:book_id>/delete', methods=['POST'])
@login_required
def admin_delete_book(book_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    logging.info(f'Admin {current_user.email} deleted book {book.title}')
    flash('Book deleted', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/api/stats')
@login_required
def api_stats():
    if current_user.role != 'admin':
        return jsonify({'error':'unauthorized'}), 403
    rows = db.session.query(Book.title, db.func.sum(Order.quantity).label('total')).join(Order).group_by(Book.id).order_by(db.func.sum(Order.quantity).desc()).limit(5).all()
    labels = [r[0] for r in rows]
    values = [int(r[1]) for r in rows]
    return jsonify({'labels': labels, 'values': values})

# Book request routes
@app.route('/request-book', methods=['GET', 'POST'])
@login_required
def request_book():
    if current_user.role != 'student':
        flash('Only students can request books', 'warning')
        return redirect(url_for('index'))
    from forms import RequestBookForm
    form = RequestBookForm()
    if form.validate_on_submit():
        book_request = BookRequest(
            user_id=current_user.id,
            title=form.title.data,
            author=form.author.data,
            genre=form.genre.data or 'General',
            reason=form.reason.data
        )
        db.session.add(book_request)
        db.session.commit()
        logging.info(f'User {current_user.email} requested book: {form.title.data}')
        flash('Book request submitted!', 'success')
        return redirect(url_for('student_dashboard'))
    return render_template('request_book.html', form=form)

@app.route('/admin/requests')
@login_required
def admin_requests():
    if current_user.role != 'admin':
        flash('Not authorized', 'danger')
        return redirect(url_for('index'))
    requests = BookRequest.query.order_by(BookRequest.created_at.desc()).all()
    return render_template('admin_requests.html', requests=requests)

@app.route('/admin/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def admin_approve_request(request_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    book_request = BookRequest.query.get_or_404(request_id)
    book_request.status = 'approved'
    db.session.commit()
    logging.info(f'Admin {current_user.email} approved book request {request_id}')
    flash('Book request approved', 'success')
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests/<int:request_id>/reject', methods=['POST'])
@login_required
def admin_reject_request(request_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    book_request = BookRequest.query.get_or_404(request_id)
    book_request.status = 'rejected'
    db.session.commit()
    logging.info(f'Admin {current_user.email} rejected book request {request_id}')
    flash('Book request rejected', 'info')
    return redirect(url_for('admin_requests'))

@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin':
        flash('Not authorized', 'danger')
        return redirect(url_for('index'))
    students = User.query.filter_by(role='student').all()
    return render_template('admin_students.html', students=students)

# --- Cart Management ---
@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/add_to_cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    qty = int(request.form.get('qty', 1))
    book = Book.query.get_or_404(book_id)
    if book.available_copies < qty:
        flash('Not enough copies available', 'warning')
        return redirect(url_for('catalog'))
    # Check if already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if cart_item:
        cart_item.quantity += qty
    else:
        cart_item = Cart(user_id=current_user.id, book_id=book_id, quantity=qty)
        db.session.add(cart_item)
    book.available_copies -= qty
    db.session.commit()
    flash('Added to cart', 'success')
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('Not authorized', 'danger')
        return redirect(url_for('cart'))
    # Return copies to inventory
    cart_item.book.available_copies += cart_item.quantity
    db.session.delete(cart_item)
    db.session.commit()
    flash('Removed from cart', 'info')
    return redirect(url_for('cart'))

@app.route('/cart/checkout', methods=['POST'])
@login_required
def cart_checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    payment_method = request.form.get('payment_method', 'mock')
    if not cart_items:
        flash('Cart is empty', 'warning')
        return redirect(url_for('cart'))
    # Create orders for each cart item
    for item in cart_items:
        order = Order(user_id=current_user.id, book_id=item.book_id, quantity=item.quantity, status='pending', payment_method=payment_method)
        db.session.add(order)
        db.session.delete(item)
    db.session.commit()
    flash('Order placed! Proceed to payment.', 'success')
    return redirect(url_for('student_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
