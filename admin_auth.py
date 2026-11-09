"""Local admin accounts and revocable opaque sessions. No camera/model imports."""
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager

from flask import g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

COOKIE_NAME = 'smartoffice_admin'
SESSION_SECONDS = 8 * 60 * 60


class AdminStore:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS admins (
                    username TEXT PRIMARY KEY, password_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL,
                    csrf_token TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_attempts (
                    address TEXT NOT NULL, attempted_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(address, attempted_at);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def configured(self):
        with self.connect() as db:
            return db.execute('SELECT 1 FROM admins LIMIT 1').fetchone() is not None

    def set_admin(self, username, password):
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,40}', username):
            raise ValueError('Nama pengguna harus 3–40 karakter: huruf, angka, titik, _ atau -.')
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ValueError('Kata sandi harus sepanjang 12–128 karakter.')
        password_hash = generate_password_hash(password)
        with self.connect() as db:
            db.execute('INSERT INTO admins VALUES (?,?) ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash', (username, password_hash))
            db.execute('DELETE FROM admin_sessions WHERE username=?', (username,))

    def session(self, raw_token):
        if not raw_token or len(raw_token) > 200:
            return None
        with self.connect() as db:
            row = db.execute('''SELECT s.* FROM admin_sessions s JOIN admins a ON s.username=a.username
                WHERE token_hash=? AND expires_at>?''', (hashlib.sha256(raw_token.encode()).hexdigest(), time.time())).fetchone()
        return dict(row) if row else None


def register_admin_auth(app, store=None):
    store = store or AdminStore(os.environ.get('SMARTOFFICE_AUTH_DB', str(Path(app.root_path) / 'instance' / 'admin_auth.db')))
    app.extensions['admin_store'] = store
    app.config.setdefault('ADMIN_COOKIE_SECURE', os.environ.get('SMARTOFFICE_COOKIE_SECURE') == '1')
    app.config.setdefault('ADMIN_WEB_ORIGINS', os.environ.get('SMARTOFFICE_WEB_ORIGIN', 'http://127.0.0.1:3000,http://localhost:3000').split(','))
    dummy_hash = generate_password_hash(secrets.token_urlsafe(24))

    def failure(message, status):
        return jsonify(message=message), status

    @app.before_request
    def require_admin():
        protected = request.path.startswith(('/api/', '/snapshots/', '/training_data/')) or request.path == '/video_feed'
        if not protected:
            return None
        if request.path == '/api/scd40':
            token = os.environ.get('SMARTOFFICE_DEVICE_TOKEN')
            if token and not hmac.compare_digest(request.headers.get('X-Device-Token', '').encode(), token.encode()):
                return failure('Token perangkat tidak valid.', 401)
            return None
        if request.path in ('/api/auth/session', '/api/auth/login'):
            return None
        admin_session = store.session(request.cookies.get(COOKIE_NAME))
        if not admin_session:
            return failure('Sesi admin berakhir. Silakan masuk kembali.', 401)
        g.admin_session = admin_session
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if not hmac.compare_digest(request.headers.get('X-CSRF-Token', '').encode(), admin_session['csrf_token'].encode()):
                return failure('Verifikasi sesi gagal. Muat ulang halaman dan coba lagi.', 403)

    @app.after_request
    def auth_headers(response):
        if request.path.startswith(('/api/', '/snapshots/', '/training_data/')) or request.path == '/video_feed':
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/api/auth/session')
    def admin_session_status():
        current = store.session(request.cookies.get(COOKIE_NAME))
        if not current:
            return jsonify(authenticated=False, configured=store.configured())
        return jsonify(authenticated=True, configured=True,
                       user={'username': current['username'], 'role': 'admin'}, csrf_token=current['csrf_token'])

    @app.post('/api/auth/login')
    def admin_login():
        # JSON + custom header prevents cross-origin HTML-form login CSRF.
        origin = request.headers.get('Origin')
        allowed_origins = [item.strip().rstrip('/') for item in app.config['ADMIN_WEB_ORIGINS']]
        allowed_origins.append(request.host_url.rstrip('/'))
        if request.headers.get('X-SmartOffice-Client') != 'web' or (origin and origin.rstrip('/') not in allowed_origins):
            return failure('Permintaan masuk tidak berasal dari aplikasi.', 403)
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
            return failure('Isi nama pengguna dan kata sandi.', 400)
        if len(data['username']) > 40 or len(data['password']) > 128:
            return failure('Nama pengguna atau kata sandi tidak sesuai.', 400)
        if not store.configured():
            return failure('Akun admin belum dibuat. Jalankan python manage_admin.py pada komputer server.', 503)
        address = request.remote_addr or 'unknown'
        now = time.time()
        with store.connect() as db:
            db.execute('DELETE FROM login_attempts WHERE attempted_at<?', (now - 900,))
            db.execute('DELETE FROM admin_sessions WHERE expires_at<=?', (now,))
            attempts = db.execute('SELECT COUNT(*) FROM login_attempts WHERE address=?', (address,)).fetchone()[0]
            if attempts >= 10:
                response = jsonify(message='Terlalu banyak percobaan. Coba lagi setelah 15 menit.')
                response.headers['Retry-After'] = '900'
                return response, 429
            account = db.execute('SELECT * FROM admins WHERE username=?', (data['username'],)).fetchone()
            valid = check_password_hash(account['password_hash'] if account else dummy_hash, data['password'])
            if not account or not valid:
                db.execute('INSERT INTO login_attempts VALUES (?,?)', (address, now))
                return failure('Nama pengguna atau kata sandi tidak sesuai.', 401)
            raw_token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
            previous = request.cookies.get(COOKIE_NAME)
            if previous:
                db.execute('DELETE FROM admin_sessions WHERE token_hash=?', (hashlib.sha256(previous.encode()).hexdigest(),))
            db.execute('INSERT INTO admin_sessions VALUES (?,?,?,?)',
                       (hashlib.sha256(raw_token.encode()).hexdigest(), account['username'], csrf, now + SESSION_SECONDS))
            db.execute('DELETE FROM login_attempts WHERE address=?', (address,))
        response = jsonify(authenticated=True, user={'username': account['username'], 'role': 'admin'}, csrf_token=csrf)
        response.set_cookie(COOKIE_NAME, raw_token, httponly=True, secure=app.config['ADMIN_COOKIE_SECURE'],
                            samesite='Lax', max_age=SESSION_SECONDS, path='/')
        return response

    @app.post('/api/auth/logout')
    def admin_logout():
        with store.connect() as db:
            db.execute('DELETE FROM admin_sessions WHERE token_hash=?', (g.admin_session['token_hash'],))
        response = jsonify(message='Anda telah keluar dari sesi admin.')
        response.delete_cookie(COOKIE_NAME, path='/', httponly=True,
                               secure=app.config['ADMIN_COOKIE_SECURE'], samesite='Lax')
        return response

    return store
