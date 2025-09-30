import sqlite3
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from dateutil.relativedelta import relativedelta
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')

DATABASE = 'database.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['email'])
    return None

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            monthly_income REAL NOT NULL,
            savings_goal REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_budget(user_id):
    """Get user budget settings"""
    conn = get_db_connection()
    budget = conn.execute('SELECT * FROM user_budget WHERE user_id = ?', (user_id,)).fetchone()
    if not budget:
        conn.execute('INSERT INTO user_budget (user_id, monthly_income, savings_goal) VALUES (?, ?, ?)', 
                    (user_id, 5000.0, 1000.0))
        conn.commit()
        budget = conn.execute('SELECT * FROM user_budget WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return budget

def get_expenses(user_id, category=None, start_date=None, end_date=None, search=None, sort_by='date', sort_order='DESC'):
    """Get expenses with optional filters"""
    conn = get_db_connection()
    query = 'SELECT * FROM expenses WHERE user_id = ?'
    params = [user_id]
    
    if category and category != 'All':
        query += ' AND category = ?'
        params.append(category)
    
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    
    if search:
        query += ' AND (note LIKE ? OR category LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if sort_by in ['date', 'amount', 'category']:
        safe_order = 'ASC' if sort_order == 'ASC' else 'DESC'
        query += f' ORDER BY {sort_by} {safe_order}'
    
    expenses = conn.execute(query, params).fetchall()
    conn.close()
    return expenses

def calculate_category_spending(user_id):
    """Calculate spending by category for pie chart"""
    conn = get_db_connection()
    result = conn.execute('''
        SELECT category, SUM(amount) as total 
        FROM expenses 
        WHERE user_id = ?
        GROUP BY category
    ''', (user_id,)).fetchall()
    conn.close()
    return result

def calculate_daily_spending(user_id, period='month'):
    """Calculate daily/weekly/monthly spending for bar chart"""
    conn = get_db_connection()
    
    if period == 'week':
        days_back = 7
    elif period == 'month':
        days_back = 30
    else:
        days_back = 30
    
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    result = conn.execute('''
        SELECT date, SUM(amount) as total 
        FROM expenses 
        WHERE user_id = ? AND date >= ?
        GROUP BY date 
        ORDER BY date
    ''', (user_id, cutoff_date)).fetchall()
    conn.close()
    return result

def forecast_next_month(user_id):
    """Forecast next month's expenses using simple moving average"""
    conn = get_db_connection()
    
    three_months_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    result = conn.execute('''
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND date >= ?
        GROUP BY month
        ORDER BY month
    ''', (user_id, three_months_ago)).fetchall()
    conn.close()
    
    if len(result) == 0:
        return 0
    
    total_spending = sum([row['total'] for row in result])
    avg_monthly = total_spending / max(len(result), 1)
    return round(avg_monthly, 2)

def get_monthly_trend(user_id):
    """Get monthly spending trend for line chart with forecast"""
    conn = get_db_connection()
    
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    result = conn.execute('''
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND date >= ?
        GROUP BY month
        ORDER BY month
    ''', (user_id, six_months_ago)).fetchall()
    conn.close()
    
    monthly_data = {}
    for row in result:
        monthly_data[row['month']] = row['total']
    
    next_month = (datetime.now() + relativedelta(months=1)).strftime('%Y-%m')
    forecast_amount = forecast_next_month(user_id)
    monthly_data[next_month] = forecast_amount
    
    return monthly_data

def get_top_expenses(user_id, limit=3):
    """Get top N highest expenses"""
    conn = get_db_connection()
    expenses = conn.execute('''
        SELECT * FROM expenses 
        WHERE user_id = ?
        ORDER BY amount DESC 
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return expenses

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long!', 'danger')
            return redirect(url_for('signup'))
        
        conn = get_db_connection()
        
        existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', 
                                     (username, email)).fetchone()
        if existing_user:
            flash('Username or email already exists!', 'danger')
            conn.close()
            return redirect(url_for('signup'))
        
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                    (username, email, password_hash))
        conn.commit()
        conn.close()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'], user['email'])
            login_user(user_obj)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Main dashboard route"""
    category_filter = request.args.get('category', 'All')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'DESC')
    
    expenses = get_expenses(current_user.id, category_filter, start_date, end_date, search, sort_by, sort_order)
    budget = get_budget(current_user.id)
    category_spending = calculate_category_spending(current_user.id)
    daily_spending = calculate_daily_spending(current_user.id, 'month')
    forecast = forecast_next_month(current_user.id)
    top_expenses = get_top_expenses(current_user.id, 3)
    monthly_trend = get_monthly_trend(current_user.id)
    
    total_spent = sum([expense['amount'] for expense in expenses])
    remaining_budget = budget['monthly_income'] - total_spent if budget else 0
    
    categories = ['Food', 'Rent', 'Travel', 'Entertainment', 'Bills', 'Other']
    
    category_data = {cat: 0 for cat in categories}
    for row in category_spending:
        if row['category'] in category_data:
            category_data[row['category']] = row['total']
    
    daily_data = {}
    for row in daily_spending:
        daily_data[row['date']] = row['total']
    
    return render_template('dashboard.html',
                         expenses=expenses,
                         budget=budget,
                         total_spent=total_spent,
                         remaining_budget=remaining_budget,
                         category_data=category_data,
                         daily_data=daily_data,
                         monthly_trend=monthly_trend,
                         forecast=forecast,
                         top_expenses=top_expenses,
                         categories=categories,
                         category_filter=category_filter,
                         start_date=start_date,
                         end_date=end_date,
                         search=search,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    """Add new expense"""
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date']
        note = request.form.get('note', '')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO expenses (user_id, amount, category, date, note) VALUES (?, ?, ?, ?, ?)',
                    (current_user.id, amount, category, date, note))
        conn.commit()
        conn.close()
        
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    categories = ['Food', 'Rent', 'Travel', 'Entertainment', 'Bills', 'Other']
    return render_template('add_expense.html', categories=categories)

@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    """Edit existing expense"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date']
        note = request.form.get('note', '')
        
        conn.execute('UPDATE expenses SET amount = ?, category = ?, date = ?, note = ? WHERE id = ? AND user_id = ?',
                    (amount, category, date, note, expense_id, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    expense = conn.execute('SELECT * FROM expenses WHERE id = ? AND user_id = ?', 
                          (expense_id, current_user.id)).fetchone()
    conn.close()
    
    if not expense:
        flash('Expense not found!', 'danger')
        return redirect(url_for('dashboard'))
    
    categories = ['Food', 'Rent', 'Travel', 'Entertainment', 'Bills', 'Other']
    return render_template('edit_expense.html', expense=expense, categories=categories)

@app.route('/delete/<int:expense_id>')
@login_required
def delete_expense(expense_id):
    """Delete expense"""
    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ? AND user_id = ?', (expense_id, current_user.id))
    conn.commit()
    conn.close()
    
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/set_budget', methods=['GET', 'POST'])
@login_required
def set_budget():
    """Set monthly income and savings goal"""
    if request.method == 'POST':
        monthly_income = request.form['monthly_income']
        savings_goal = request.form['savings_goal']
        
        conn = get_db_connection()
        conn.execute('UPDATE user_budget SET monthly_income = ?, savings_goal = ? WHERE user_id = ?',
                    (monthly_income, savings_goal, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Budget settings updated!', 'success')
        return redirect(url_for('dashboard'))
    
    budget = get_budget(current_user.id)
    return render_template('set_budget.html', budget=budget)

@app.route('/export')
@login_required
def export_expenses():
    """Export current month's expenses to CSV"""
    current_month = datetime.now().strftime('%Y-%m')
    
    conn = get_db_connection()
    expenses = conn.execute('''
        SELECT * FROM expenses 
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        ORDER BY date DESC
    ''', (current_user.id, current_month)).fetchall()
    conn.close()
    
    df = pd.DataFrame([dict(expense) for expense in expenses])
    
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    filename = f'expenses_{current_month}.csv'
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
