from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'exam_secret_key'

# --- БАЗА ДАННЫХ ---
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, login TEXT UNIQUE, full_name TEXT, role TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, category TEXT, size INTEGER,
        price REAL, quantity INTEGER, image TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, user_login TEXT, product_id INTEGER,
        quantity INTEGER, total REAL, date TEXT)''')
    if not cur.execute("SELECT * FROM users").fetchone():
        cur.execute("INSERT INTO users VALUES (1, 'admin', 'Администратор', 'admin')")
        cur.execute("INSERT INTO users VALUES (2, 'user', 'Иван Иванов', 'user')")
    if not cur.execute("SELECT * FROM products").fetchone():
        cur.execute("INSERT INTO products VALUES (1, 'Кроссовки Nike', 'Спортивная', 42, 5000, 10, '')")
        cur.execute("INSERT INTO products VALUES (2, 'Ботинки Timberland', 'Зимняя', 43, 8000, 3, '')")
    conn.commit()
    conn.close()

# --- HTML-СТРАНИЦЫ ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
        conn.close()
        if user:
            session['user'] = user['login']
            session['role'] = user['role']
            return redirect(url_for('catalog'))
        return "Пользователь не найден"
    return render_template('login.html')

@app.route('/catalog')
def catalog():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('catalog.html', products=products)

@app.route('/order/<int:product_id>', methods=['POST'])
def order(product_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    quantity = int(request.form['quantity'])
    conn = get_db()
    price = conn.execute("SELECT price FROM products WHERE id = ?", (product_id,)).fetchone()['price']
    total = price * quantity
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute("INSERT INTO orders (user_login, product_id, quantity, total, date) VALUES (?,?,?,?,?)",
                 (session['user'], product_id, quantity, total, date))
    conn.commit()
    conn.close()
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    orders = conn.execute("SELECT o.*, p.name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.user_login = ?",
                          (session['user'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

# --- API (JSON) ---
@app.route('/api/products')
def api_products():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/orders')
def api_orders():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 401
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_login = ?", (session['user'],)).fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])

@app.route('/api/order', methods=['POST'])
def api_create_order():
    if 'user' not in session:
        return jsonify({"error": "Не авторизован"}), 401
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    conn = get_db()
    price = conn.execute("SELECT price FROM products WHERE id = ?", (product_id,)).fetchone()['price']
    total = price * quantity
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute("INSERT INTO orders (user_login, product_id, quantity, total, date) VALUES (?,?,?,?,?)",
                 (session['user'], product_id, quantity, total, date))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "total": total}), 201

# --- ЗАПУСК ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0')