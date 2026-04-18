from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_mysqldb import MySQL
from datetime import datetime
import bcrypt
import os
from dotenv import load_dotenv  # Import dotenv
import smtplib
from email.mime.text import MIMEText

# Load environment variables from .env
load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(_BASE_DIR, 'static'),
    template_folder=os.path.join(_BASE_DIR, 'templates'),
)

# Secret Key for session management
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config.get('SECRET_KEY'):
    # Keep DB connectivity untouched; this only enables sessions/flash.
    app.config['SECRET_KEY'] = os.urandom(32)

# MySQL Configuration for live database
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT'))
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Email credentials
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')

mysql = MySQL(app)


def _get_db():
    """
    flask_mysqldb's `.connection` is broken for Flask<3 in some versions because it
    captures `_app_ctx_stack.top` at import time. Use `.connect` instead.
    """
    return mysql.connect

# Before request handler to ensure the user is logged in
@app.before_request
def check_user_logged_in():
    if 'username' not in session and request.endpoint not in ['login', 'register', 'landing', 'check_username', 'privacy_policy', 'termsofservice', 'about', 'contact']:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))


@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = _get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM credentials WHERE username = %s", (username,))
            user = cur.fetchone()  # This will return a dictionary
            cur.close()
            conn.close()
        except Exception:
            app.logger.exception("Login failed due to database connection error")
            flash('Service temporarily unavailable. Please try again in a moment.', 'danger')
            return render_template('login.html'), 503

        if user:
            # Check if the password is correct
            stored_password = user.get('password')
            if isinstance(stored_password, memoryview):
                stored_password = stored_password.tobytes()
            elif isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')

            if not isinstance(stored_password, (bytes, bytearray)):
                flash('Invalid password format stored for this user. Please reset your password.', 'danger')
                return render_template('login.html'), 400

            if bcrypt.checkpw(password.encode('utf-8'), bytes(stored_password)):
                # If the password is correct, log in the user
                session['username'] = username
                return redirect(url_for('index'))  # Redirect to the index page after successful login
            else:
                flash('Invalid password!', 'danger')
        else:
            flash('Username not found, please register!', 'warning')
            return redirect(url_for('register'))  # Redirect to the register page if the username is not found
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hash password before storing it
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            conn = _get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM credentials WHERE username = %s", (username,))
            existing_user = cur.fetchone()
        except Exception:
            app.logger.exception("Registration failed due to database connection error")
            flash('Service temporarily unavailable. Please try again in a moment.', 'danger')
            return render_template('register.html'), 503

        if existing_user:
            flash('User already exists! Please login.', 'warning')
            return redirect(url_for('login'))  # Redirect to login if the user already exists

        # Insert new user into the credentials table
        cur.execute("INSERT INTO credentials (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        cur.close()
        conn.close()

        # Automatically log in the user after registration
        session['username'] = username  # Store session data
        # flash('Registration successful! You are now logged in.', 'success')

        return redirect(url_for('index'))  # Redirect to index.html after successful registration

    return render_template('register.html')


@app.route('/check_username', methods=['POST'])
def check_username():
    data = request.get_json()
    username = data.get('username')

    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM credentials WHERE username = %s", (username,))
        existing_user = cur.fetchone()
        cur.close()
        conn.close()
    except Exception:
        app.logger.exception("Username check failed due to database connection error")
        return jsonify({'exists': False, 'error': 'service_unavailable'}), 503
    
    return jsonify({'exists': bool(existing_user)})  # Returns True if user exists, False otherwise


@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove the user from session
    return redirect(url_for('landing'))  # Redirect to login page after logout

@app.route('/index')
def index():
    username = session.get('username')  # Get the logged-in username

    conn = _get_db()
    cur = conn.cursor()
    current_month = datetime.now().strftime('%Y-%m')
    current_month_name = datetime.now().strftime('%B %Y')  # "January 2025"

    # Get user_id from the credentials table
    cur.execute("SELECT id FROM credentials WHERE username = %s", [username])
    user = cur.fetchone()

    if user:
        user_id = user['id']
        query = "SELECT * FROM expenses WHERE DATE_FORMAT(date, '%%Y-%%m') = %s AND user_id = %s"
        cur.execute(query, (current_month, user_id))
        expenses = cur.fetchall()
        total = sum(expense['amount'] for expense in expenses)
        cur.close()
        conn.close()
        return render_template('index.html', expenses=expenses, total=total, current_month_name=current_month_name)
    else:
        flash('User not found!', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add_expense():
    data = request.get_json()
    date = data['date']
    type = data['type']
    amount = data['amount']
    username = session.get('username')  # Get the logged-in username

    # Get the user_id from the credentials table
    conn = _get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM credentials WHERE username = %s", [username])
    user = cur.fetchone()

    if user:
        user_id = user['id']
        cur.execute("INSERT INTO expenses (date, type, amount, user_id) VALUES (%s, %s, %s, %s)", 
                    (date, type, amount, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(success=True)
    else:
        cur.close()
        conn.close()
        return jsonify(error="User not found"), 404

@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_expense(id):
    try:
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True}), 200  # Ensure JSON response with 200 status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
 



@app.route('/visualize', methods=['GET', 'POST'])
def visualize():
    username = session.get('username')  # Get the logged-in username
    if request.method == 'POST':
        data = request.get_json()
        year = int(data['year'])
        search_query = data.get('search_query', '')  # Get the search query if provided
    else:
        year = datetime.now().year
        search_query = ''

    conn = _get_db()
    cur = conn.cursor()

    # Get user_id from the credentials table
    cur.execute("SELECT id FROM credentials WHERE username = %s", [username])
    user = cur.fetchone()

    if user:
        user_id = user['id']
        # Fetch expenses for each month of the selected year
        query = """
            SELECT MONTH(date) AS month, SUM(amount) AS total_expenses
            FROM expenses
            WHERE YEAR(date) = %s AND user_id = %s
        """
        params = [year, user_id]

        # Add search query to filter by item name
        if search_query:
            query += " AND type LIKE %s"
            params.append('%' + search_query + '%')

        query += " GROUP BY MONTH(date)"
        cur.execute(query, params)
        monthly_expenses = cur.fetchall()

        # Prepare data for visualization
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        expense_data = [0] * 12  # Default values for all months

        for expense in monthly_expenses:
            expense_data[expense['month'] - 1] = expense['total_expenses']

        total_spent = sum(expense_data)  # Calculate total amount spent

        cur.close()
        conn.close()

        if request.method == 'POST':
            return jsonify(months=months, expense_data=expense_data, total_spent=total_spent)
        else:
            return render_template('visualize.html', months=months, expense_data=expense_data, year=year, total_spent=total_spent)
    else:
        flash('User not found!', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('login'))


@app.route('/reports', methods=['GET', 'POST'])
def filter_expenses():
    username = session.get('username')  # Get the logged-in username
    conn = _get_db()
    cur = conn.cursor()

    # Get user_id from the credentials table
    cur.execute("SELECT id FROM credentials WHERE username = %s", [username])
    user = cur.fetchone()

    if user:
        user_id = user['id']

        # Get the current year and all available years in the database
        cur.execute("SELECT DISTINCT YEAR(date) FROM expenses WHERE user_id = %s ORDER BY YEAR(date) DESC", [user_id])
        years = [row['YEAR(date)'] for row in cur.fetchall()]

        # Default to the current month and year if no filter is applied
        selected_year = int(request.form.get('year', datetime.now().year))
        selected_month = int(request.form.get('month', datetime.now().month))

        # Query to filter expenses based on selected year and month
        query = """
        SELECT * FROM expenses
        WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        ORDER BY date ASC
        """
        cur.execute(query, (selected_year, selected_month, user_id))
        expenses = cur.fetchall()

        # Calculate total expenses for the selected month and year
        total = sum(expense['amount'] for expense in expenses)

        # Mapping of month numbers to month names
        months = {
            1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
        }

        # Close the cursor
        cur.close()
        conn.close()

        # Return the rendered template with total added to the context
        return render_template(
            'reports.html', 
            expenses=expenses, 
            years=years,
            months=months,
            selected_year=selected_year,
            selected_month=selected_month,
            total=total  # Pass total expense for the selected month to the template
        )
    else:
        flash('User not found!', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('login'))
    

@app.route('/footer/privacy_policy')
def privacy_policy():
    return render_template('footer/privacy_policy.html')

@app.route('/footer/termsofservice')
def termsofservice():
    return render_template('footer/termsofservice.html')

@app.route('/footer/about')
def about():
    return render_template('footer/about.html')

@app.route('/footer/contact')
def contact_form():
    return render_template('footer/contact.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        structured_message = f"""
        New Contact Form Submission:

        Name: {name}
        Email: {email}

        Message:
        {message}
        """

        # Send email
        msg = MIMEText(structured_message)
        msg["Subject"] = "Tracklio Query"
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

            flash("Your message has been sent successfully!", "success")
        except Exception as e:
            flash("An error occurred. Please try again later.", "error")
            print("Error sending email:", e)

        return redirect(url_for('contact'))

    return render_template("footer/contact.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0')
