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
                return redirect(url_for('visualize'))  # Redirect to the visualize dashboard after successful login
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

        return redirect(url_for('visualize'))  # Redirect to visualize dashboard after successful registration

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
    return redirect(url_for('visualize'))

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
    if not username:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            data = request.get_json() or {}
            month_year = data.get('month_year')
            search_query = data.get('search_query', '').strip()
        except Exception:
            month_year = None
            search_query = ''

        if month_year:
            try:
                year, month = map(int, month_year.split('-'))
            except Exception:
                now = datetime.now()
                year = now.year
                month = now.month
        else:
            now = datetime.now()
            year = now.year
            month = now.month

        import calendar
        days_in_month = calendar.monthrange(year, month)[1]

        conn = _get_db()
        cur = conn.cursor()

        # Get user_id from the credentials table
        cur.execute("SELECT id FROM credentials WHERE username = %s", [username])
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return jsonify(error="User not found"), 404

        user_id = user['id']

        # 1. Total spent in this month
        total_query = """
            SELECT SUM(amount) AS total 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            total_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        
        cur.execute(total_query, params)
        total_res = cur.fetchone()
        total_spent = float(total_res['total']) if total_res and total_res['total'] is not None else 0.0

        # 2. Total transactions
        count_query = """
            SELECT COUNT(*) AS count 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            count_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        
        cur.execute(count_query, params)
        count_res = cur.fetchone()
        transaction_count = count_res['count'] if count_res else 0

        # 3. Average spending per day
        avg_per_day = round(total_spent / days_in_month, 2)

        # 4. Peak day
        peak_query = """
            SELECT DAY(date) AS day, SUM(amount) AS total 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            peak_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        peak_query += " GROUP BY DAY(date) ORDER BY total DESC LIMIT 1"
        
        cur.execute(peak_query, params)
        peak_res = cur.fetchone()
        peak_day_num = peak_res['day'] if peak_res else "N/A"
        peak_day_amount = float(peak_res['total']) if peak_res else 0.0

        # 5. Daily spend trend (day-by-day totals)
        daily_query = """
            SELECT DAY(date) AS day, SUM(amount) AS total 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            daily_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        daily_query += " GROUP BY DAY(date)"
        
        cur.execute(daily_query, params)
        daily_res = cur.fetchall()
        daily_dict = {row['day']: float(row['total']) for row in daily_res}
        
        daily_days = list(range(1, days_in_month + 1))
        daily_totals = [daily_dict.get(day, 0.0) for day in daily_days]

        # 6. Top Items / Categories (Donut chart data)
        cat_query = """
            SELECT type, SUM(amount) AS total 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            cat_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        cat_query += " GROUP BY type ORDER BY total DESC"
        
        cur.execute(cat_query, params)
        cat_res = cur.fetchall()
        
        categories = []
        category_totals = []
        category_percentages = []
        
        if cat_res:
            sorted_cats = [{ 'name': row['type'], 'total': float(row['total']) } for row in cat_res]
            if len(sorted_cats) > 4:
                top_cats = sorted_cats[:3]
                other_sum = sum(item['total'] for item in sorted_cats[3:])
                top_cats.append({ 'name': 'Other', 'total': other_sum })
            else:
                top_cats = sorted_cats
                
            for item in top_cats:
                categories.append(item['name'])
                category_totals.append(item['total'])
                percentage = round((item['total'] / total_spent) * 100, 1) if total_spent > 0 else 0
                category_percentages.append(percentage)

        # 7. Monthly spending for the selected year
        year_query = """
            SELECT MONTH(date) AS month, SUM(amount) AS total 
            FROM expenses 
            WHERE YEAR(date) = %s AND user_id = %s
        """
        params = [year, user_id]
        if search_query:
            year_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        year_query += " GROUP BY MONTH(date)"
        
        cur.execute(year_query, params)
        year_res = cur.fetchall()
        year_dict = {row['month']: float(row['total']) for row in year_res}
        
        months_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_totals = [year_dict.get(m, 0.0) for m in range(1, 13)]
        yearly_total = sum(monthly_totals)
        
        # Highlight highest spending month
        max_spent = max(monthly_totals) if monthly_totals else 0
        if max_spent > 0:
            highest_month_idx = monthly_totals.index(max_spent)
            highest_month_name = months_names[highest_month_idx]
        else:
            highest_month_name = "N/A"
            
        # Percentage change compared to previous month
        selected_month_total = monthly_totals[month - 1]
        prev_month_total = monthly_totals[month - 2] if month > 1 else 0.0
        
        if prev_month_total > 0:
            percentage_change = round(((selected_month_total - prev_month_total) / prev_month_total) * 100)
        else:
            percentage_change = 100 if selected_month_total > 0 else 0

        # 8. Smart Insights
        # 8.1. Top Category
        top_category_name = categories[0] if categories else "N/A"
        top_category_amount = category_totals[0] if category_totals else 0.0
        top_category_percentage = category_percentages[0] if category_percentages else 0.0
        
        # 8.2. Highest Spending Day
        # Already have peak_day_num and peak_day_amount
        
        # 8.3. Most Frequent Expense Item
        freq_query = """
            SELECT type, COUNT(*) AS count 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            freq_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        freq_query += " GROUP BY type ORDER BY count DESC LIMIT 1"
        
        cur.execute(freq_query, params)
        freq_res = cur.fetchone()
        frequent_item_name = freq_res['type'] if freq_res else "N/A"
        frequent_item_count = freq_res['count'] if freq_res else 0

        # 8.4. Weekday vs Weekend split
        pattern_query = """
            SELECT 
                SUM(CASE WHEN DAYOFWEEK(date) IN (1, 7) THEN amount ELSE 0 END) AS weekend_spent,
                SUM(CASE WHEN DAYOFWEEK(date) IN (2, 3, 4, 5, 6) THEN amount ELSE 0 END) AS weekday_spent
            FROM expenses
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            pattern_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
            
        cur.execute(pattern_query, params)
        pattern_res = cur.fetchone()
        
        weekend_spent = float(pattern_res['weekend_spent']) if pattern_res and pattern_res['weekend_spent'] is not None else 0.0
        weekday_spent = float(pattern_res['weekday_spent']) if pattern_res and pattern_res['weekday_spent'] is not None else 0.0
        total_pattern = weekend_spent + weekday_spent
        
        if total_pattern > 0:
            weekday_percentage = round((weekday_spent / total_pattern) * 100)
            weekend_percentage = round((weekend_spent / total_pattern) * 100)
        else:
            weekday_percentage = 0
            weekend_percentage = 0

        # 9. List of expenses for table
        list_query = """
            SELECT id, DATE_FORMAT(date, '%%Y-%%m-%%d') AS date, type, amount 
            FROM expenses 
            WHERE YEAR(date) = %s AND MONTH(date) = %s AND user_id = %s
        """
        params = [year, month, user_id]
        if search_query:
            list_query += " AND type LIKE %s"
            params.append('%' + search_query + '%')
        list_query += " ORDER BY date ASC"
        
        cur.execute(list_query, params)
        expenses_res = cur.fetchall()
        
        expenses_list = []
        for row in expenses_res:
            expenses_list.append({
                'id': row['id'],
                'date': row['date'],
                'type': row['type'],
                'amount': float(row['amount'])
            })

        cur.close()
        conn.close()

        return jsonify(
            success=True,
            total_spent=total_spent,
            transaction_count=transaction_count,
            avg_per_day=avg_per_day,
            peak_day_num=peak_day_num,
            peak_day_amount=peak_day_amount,
            daily_days=daily_days,
            daily_totals=daily_totals,
            categories=categories,
            category_totals=category_totals,
            category_percentages=category_percentages,
            months_names=months_names,
            monthly_totals=monthly_totals,
            yearly_total=yearly_total,
            highest_month_name=highest_month_name,
            percentage_change=percentage_change,
            top_category_name=top_category_name,
            top_category_amount=top_category_amount,
            top_category_percentage=top_category_percentage,
            frequent_item_name=frequent_item_name,
            frequent_item_count=frequent_item_count,
            weekday_percentage=weekday_percentage,
            weekend_percentage=weekend_percentage,
            expenses=expenses_list
        )

    else:
        # GET request returns the main view template
        now = datetime.now()
        current_month_year = now.strftime('%Y-%m')
        return render_template('visualize.html', current_month_year=current_month_year)


@app.route('/reports', methods=['GET', 'POST'])
def filter_expenses():
    return redirect(url_for('visualize'))
    

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
