from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import mysql.connector

app = Flask(__name__)
app.secret_key = 'daffa-akbar'  # ganti dengan string acak yang panjang

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="WebPenjualan"
    )

# ── DECORATORS ────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            return render_template('forbidden.html'), 403
        return f(*args, **kwargs)
    return decorated

# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        if user and user['password'] == password:
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            return redirect(url_for('index'))
        else:
            error = 'Username atau password salah.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── MAIN PAGE ─────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produk ORDER BY nama_produk")
    produk_list = cursor.fetchall()
    cursor.execute("""
        SELECT j.id_penjualan, p.id_produk, p.nama_produk,
               p.harga_modal, p.harga_jual, j.jumlah_terjual,
               (p.harga_jual * j.jumlah_terjual) AS pendapatan_kotor,
               ((p.harga_jual - p.harga_modal) * j.jumlah_terjual) AS pendapatan_bersih
        FROM penjualan j
        JOIN produk p ON j.id_produk = p.id_produk
        ORDER BY j.id_penjualan DESC
    """)
    laporan = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('index.html', laporan=laporan, produk_list=produk_list,
                           username=session['username'], role=session['role'])

# ── PRODUK (ADMIN ONLY) ───────────────────────────────────────────────────────
@app.route('/tambah_produk', methods=['POST'])
@admin_required
def tambah_produk():
    nama  = request.form['nama_produk']
    modal = request.form['harga_modal']
    jual  = request.form['harga_jual']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO produk (nama_produk, harga_modal, harga_jual) VALUES (%s, %s, %s)", (nama, modal, jual))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

@app.route('/hapus_produk/<int:id_produk>', methods=['POST'])
@admin_required
def hapus_produk(id_produk):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM penjualan WHERE id_produk = %s", (id_produk,))
    cursor.execute("DELETE FROM produk WHERE id_produk = %s", (id_produk,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

# ── PENJUALAN ─────────────────────────────────────────────────────────────────
@app.route('/tambah_penjualan', methods=['POST'])
@login_required
def tambah_penjualan():
    id_produk = request.form['id_produk']
    jumlah    = request.form['jumlah_terjual']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO penjualan (id_produk, jumlah_terjual) VALUES (%s, %s)", (id_produk, jumlah))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

@app.route('/hapus_transaksi/<int:id_penjualan>', methods=['POST'])
@admin_required
def hapus_transaksi(id_penjualan):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM penjualan WHERE id_penjualan = %s", (id_penjualan,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

# ── MANAJEMEN USER (ADMIN ONLY) ───────────────────────────────────────────────
@app.route('/users')
@admin_required
def users():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, username, role FROM users ORDER BY id")
    user_list = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('users.html', user_list=user_list,
                           username=session['username'], role=session['role'])

@app.route('/tambah_user', methods=['POST'])
@admin_required
def tambah_user():
    uname = request.form['username'].strip()
    pwd   = request.form['password']
    role  = request.form['role']
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (uname, pwd, role))
        db.commit()
    except Exception:
        pass
    cursor.close()
    db.close()
    return redirect(url_for('users'))

@app.route('/hapus_user/<int:id_user>', methods=['POST'])
@admin_required
def hapus_user(id_user):
    if id_user == session['user_id']:
        return redirect(url_for('users'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (id_user,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('users'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)