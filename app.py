from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import mysql.connector

app = Flask(__name__)
app.secret_key = 'rahasia-ganti-ini-xyz-999'

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host="localhost", user="root", password="", database="WebPenjualan"
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

# ── AUTH: REGISTER ────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm  = request.form['confirm_password']

        if not username or not password:
            error = 'Username dan password tidak boleh kosong.'
        elif len(password) < 4:
            error = 'Password minimal 4 karakter.'
        elif password != confirm:
            error = 'Password dan konfirmasi tidak cocok.'
        else:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing = cursor.fetchone()
            if existing:
                error = 'Username sudah dipakai, coba yang lain.'
            else:
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')",
                    (username, password)
                )
                db.commit()
                user_id = cursor.lastrowid
                cursor.close()
                db.close()
                session['user_id']  = user_id
                session['username'] = username
                session['role']     = 'user'
                return redirect(url_for('index'))
            cursor.close()
            db.close()

    return render_template('register.html', error=error)

# ── AUTH: LOGIN ───────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
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

# ── INDEX ─────────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    db     = get_db()
    cursor = db.cursor(dictionary=True)
    uid    = session['user_id']
    role   = session['role']

    # Admin lihat semua, user lihat milik sendiri
    if role == 'admin':
        cursor.execute("SELECT * FROM produk ORDER BY nama_produk")
        produk_list = cursor.fetchall()
        cursor.execute("""
            SELECT j.id_penjualan, u.username, p.id_produk, p.nama_produk,
                   p.harga_modal, p.harga_jual, j.jumlah_terjual, j.tanggal,
                   (p.harga_jual * j.jumlah_terjual) AS pendapatan_kotor,
                   ((p.harga_jual - p.harga_modal) * j.jumlah_terjual) AS pendapatan_bersih
            FROM penjualan j
            JOIN produk p ON j.id_produk = p.id_produk
            JOIN users  u ON j.id_user   = u.id
            ORDER BY j.id_penjualan DESC
        """)
    else:
        cursor.execute("SELECT * FROM produk WHERE id_user = %s ORDER BY nama_produk", (uid,))
        produk_list = cursor.fetchall()
        cursor.execute("""
            SELECT j.id_penjualan, p.id_produk, p.nama_produk,
                   p.harga_modal, p.harga_jual, j.jumlah_terjual, j.tanggal,
                   (p.harga_jual * j.jumlah_terjual) AS pendapatan_kotor,
                   ((p.harga_jual - p.harga_modal) * j.jumlah_terjual) AS pendapatan_bersih
            FROM penjualan j
            JOIN produk p ON j.id_produk = p.id_produk
            WHERE j.id_user = %s
            ORDER BY j.id_penjualan DESC
        """, (uid,))

    laporan = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('index.html',
                           laporan=laporan, produk_list=produk_list,
                           username=session['username'], role=role)

# ── PRODUK ────────────────────────────────────────────────────────────────────
@app.route('/tambah_produk', methods=['POST'])
@login_required
def tambah_produk():
    uid   = session['user_id']
    nama  = request.form['nama_produk']
    modal = request.form['harga_modal']
    jual  = request.form['harga_jual']
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produk (id_user, nama_produk, harga_modal, harga_jual) VALUES (%s,%s,%s,%s)",
        (uid, nama, modal, jual)
    )
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

@app.route('/hapus_produk/<int:id_produk>', methods=['POST'])
@login_required
def hapus_produk(id_produk):
    uid  = session['user_id']
    role = session['role']
    db   = get_db()
    cursor = db.cursor(dictionary=True)

    # Pastikan produk milik user ini (kecuali admin)
    if role != 'admin':
        cursor.execute("SELECT id_produk FROM produk WHERE id_produk=%s AND id_user=%s", (id_produk, uid))
        if not cursor.fetchone():
            cursor.close(); db.close()
            return redirect(url_for('index'))

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
    uid       = session['user_id']
    id_produk = request.form['id_produk']
    jumlah    = request.form['jumlah_terjual']
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO penjualan (id_user, id_produk, jumlah_terjual) VALUES (%s,%s,%s)",
        (uid, id_produk, jumlah)
    )
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

@app.route('/hapus_transaksi/<int:id_penjualan>', methods=['POST'])
@login_required
def hapus_transaksi(id_penjualan):
    uid  = session['user_id']
    role = session['role']
    db   = get_db()
    cursor = db.cursor(dictionary=True)

    if role != 'admin':
        cursor.execute("SELECT id_penjualan FROM penjualan WHERE id_penjualan=%s AND id_user=%s", (id_penjualan, uid))
        if not cursor.fetchone():
            cursor.close(); db.close()
            return redirect(url_for('index'))

    cursor.execute("DELETE FROM penjualan WHERE id_penjualan = %s", (id_penjualan,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

# ── ADMIN: KELOLA USER ────────────────────────────────────────────────────────
@app.route('/users')
@admin_required
def users():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.username, u.role, u.created_at,
               COUNT(DISTINCT p.id_produk) AS total_produk,
               COUNT(DISTINCT j.id_penjualan) AS total_transaksi
        FROM users u
        LEFT JOIN produk    p ON p.id_user = u.id
        LEFT JOIN penjualan j ON j.id_user = u.id
        GROUP BY u.id ORDER BY u.id
    """)
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
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (uname, pwd, role))
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
    cursor.execute("DELETE FROM penjualan WHERE id_user = %s", (id_user,))
    cursor.execute("DELETE FROM produk    WHERE id_user = %s", (id_user,))
    cursor.execute("DELETE FROM users     WHERE id      = %s", (id_user,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('users'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)