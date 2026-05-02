from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="WebPenjualan"
    )

@app.route('/')
def index():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM produk")
    produk_list = cursor.fetchall()

    query_laporan = """
        SELECT
            j.id_penjualan,
            p.id_produk,
            p.nama_produk,
            p.harga_modal,
            p.harga_jual,
            j.jumlah_terjual,
            (p.harga_jual * j.jumlah_terjual) AS pendapatan_kotor,
            ((p.harga_jual - p.harga_modal) * j.jumlah_terjual) AS pendapatan_bersih
        FROM penjualan j
        JOIN produk p ON j.id_produk = p.id_produk
        ORDER BY j.id_penjualan DESC
    """
    cursor.execute(query_laporan)
    laporan = cursor.fetchall()
    cursor.close()  # fix: sebelumnya cursor.close (tanpa tanda kurung)
    db.close()
    return render_template('index.html', laporan=laporan, produk_list=produk_list)


@app.route('/tambah_produk', methods=['POST'])
def tambah_produk():
    nama  = request.form['nama_produk']
    modal = request.form['harga_modal']
    jual  = request.form['harga_jual']
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produk (nama_produk, harga_modal, harga_jual) VALUES (%s, %s, %s)",
        (nama, modal, jual)
    )
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))


@app.route('/tambah_penjualan', methods=['POST'])
def tambah_penjualan():
    id_produk = request.form['id_produk']
    jumlah    = request.form['jumlah_terjual']
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO penjualan (id_produk, jumlah_terjual) VALUES (%s, %s)",
        (id_produk, jumlah)
    )
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))


@app.route('/hapus_produk/<int:id_produk>', methods=['POST'])
def hapus_produk(id_produk):
    db = get_db_connection()
    cursor = db.cursor()
    # Hapus dulu transaksi yang terkait, baru hapus produknya
    cursor.execute("DELETE FROM penjualan WHERE id_produk = %s", (id_produk,))
    cursor.execute("DELETE FROM produk WHERE id_produk = %s", (id_produk,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))


@app.route('/hapus_transaksi/<int:id_penjualan>', methods=['POST'])
def hapus_transaksi(id_penjualan):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM penjualan WHERE id_penjualan = %s", (id_penjualan,))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)