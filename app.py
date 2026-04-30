from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Book
from auth_utils import role_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pokemonanddoraemon'

# --- 2. REPLACE YOUR OLD DATABASE CONFIG WITH THIS ---
uri = os.getenv("DATABASE_URL")  # This gets the link from Render's dashboard

if uri and uri.startswith("postgres://"):
    # Fix for Render/SQLAlchemy compatibility
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = 'uri'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- NEW: LOGIN ROUTE ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return "Invalid username or password", 401 # Simple error for now
            
    return render_template('login.html')

# --- NEW: LOGOUT ROUTE ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if user already exists
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            return "Username already taken!", 400
        
        # Hash password and save as 'member'
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw, role='member')
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log them in immediately or redirect to login
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('register.html')

# --- EXISTING ROUTES ---

@app.route('/')
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)

@app.route('/admin/add-book', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_book():
    if request.method == 'POST':
        new_book = Book(
            title=request.form['title'], 
            author=request.form['author'],
            is_available=True
        )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/borrow/<int:book_id>')
@login_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.is_available:
        book.is_available = False
        book.borrower_id = current_user.id  # Assign the current user's ID
        db.session.commit()
        flash(f"You have borrowed '{book.title}'", "success")
    else:
        flash("Book is already borrowed.", "danger")
    return redirect(url_for('index'))

@app.route('/return/<int:book_id>')
@login_required
def return_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # SECURITY CHECK: Is the current user the one who borrowed it?
    if book.borrower_id == current_user.id:
        book.is_available = True
        book.borrower_id = None  # Clear the borrower field
        db.session.commit()
        flash(f"Successfully returned '{book.title}'", "success")
    else:
        flash("Error: You can only return books that you borrowed!", "danger")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # --- AUTO-CREATE ADMIN IF NOT EXISTS ---
        if not User.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123')
            admin_user = User(username='admin', password=hashed_pw, role='admin')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created: admin / admin123")

    app.run(debug=True)