"""Authentication tests use an isolated DB, with no app.py/device imports."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from flask import Flask, jsonify
from werkzeug.security import check_password_hash
from admin_auth import AdminStore, COOKIE_NAME, register_admin_auth


class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = AdminStore(Path(self.temp.name) / 'auth.db')
        self.store.set_admin('admin', 'test-admin-password-2026')
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, ADMIN_WEB_ORIGINS=['http://127.0.0.1:3000'])
        register_admin_auth(self.app, self.store)
        for route in ['/api/status', '/api/sensors/export', '/video_feed', '/snapshots/test.jpg', '/training_data/test.jpg']:
            self.app.add_url_rule(route, route, lambda: jsonify(ok=True))
        self.app.add_url_rule('/api/data/clear', 'clear', lambda: jsonify(ok=True), methods=['POST'])
        self.app.add_url_rule('/api/scd40', 'scd40', lambda: jsonify(ok=True), methods=['POST'])
        self.client = self.app.test_client()
        self.headers = {'X-SmartOffice-Client': 'web', 'Origin': 'http://127.0.0.1:3000'}

    def login(self, password='test-admin-password-2026'):
        return self.client.post('/api/auth/login', json={'username': 'admin', 'password': password}, headers=self.headers)

    def test_anonymous_cannot_read_api_images_video_or_exports(self):
        for path in ['/api/status', '/api/sensors/export', '/video_feed', '/snapshots/test.jpg', '/training_data/test.jpg']:
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.post('/api/data/clear').status_code, 401)
        self.assertFalse(self.client.get('/api/auth/session').json['authenticated'])

    def test_login_sets_private_cookie_and_stores_only_hashes(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)
        self.assertIn('Max-Age=28800', cookie)
        session = self.client.get('/api/auth/session').json
        self.assertEqual(session['user'], {'username': 'admin', 'role': 'admin'})
        self.assertTrue(session['csrf_token'])
        raw = self.client.get_cookie(COOKIE_NAME).value
        with self.store.connect() as db:
            account = db.execute('SELECT * FROM admins').fetchone()
            token = db.execute('SELECT token_hash FROM admin_sessions').fetchone()[0]
        self.assertNotEqual(token, raw)
        self.assertNotEqual(account['password_hash'], 'test-admin-password-2026')
        self.assertTrue(check_password_hash(account['password_hash'], 'test-admin-password-2026'))
        self.assertEqual(self.client.get('/api/status').headers['Cache-Control'], 'no-store')

    def test_mutations_require_csrf_and_logout_revokes_replayed_cookie(self):
        self.login()
        raw = self.client.get_cookie(COOKIE_NAME).value
        self.assertEqual(self.client.post('/api/data/clear').status_code, 403)
        csrf = self.client.get('/api/auth/session').json['csrf_token']
        headers = {'X-CSRF-Token': csrf}
        self.assertEqual(self.client.post('/api/data/clear', headers=headers).status_code, 200)
        self.assertEqual(self.client.post('/api/auth/logout', headers=headers).status_code, 200)
        self.client.set_cookie(COOKIE_NAME, raw)
        self.assertEqual(self.client.get('/api/status').status_code, 401)

    def test_expiry_and_password_reset_revoke_access(self):
        self.login()
        with self.store.connect() as db:
            db.execute('UPDATE admin_sessions SET expires_at=0')
        self.assertEqual(self.client.get('/api/status').status_code, 401)
        self.login()
        self.store.set_admin('admin', 'new-admin-password-2026')
        self.assertEqual(self.client.get('/api/status').status_code, 401)
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login('new-admin-password-2026').status_code, 200)

    def test_invalid_login_and_cross_origin_are_rejected(self):
        for data in [None, [], [1], {'username': 'admin'}, {'username': 12, 'password': 'a'}]:
            self.assertEqual(self.client.post('/api/auth/login', json=data, headers=self.headers).status_code, 400)
        self.assertEqual(self.login('wrong-password').status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'test-admin-password-2026'}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/login', json={}, headers={**self.headers, 'Origin': 'https://other.example'}).status_code, 403)

    def test_missing_account_has_setup_message_and_credentials_are_validated(self):
        with self.store.connect() as db:
            db.execute('DELETE FROM admins')
        self.assertFalse(self.client.get('/api/auth/session').json['configured'])
        self.assertEqual(self.login().status_code, 503)
        for username, password in [('x', 'long-enough-password'), ('admin', 'short')]:
            with self.assertRaises(ValueError):
                self.store.set_admin(username, password)

    def test_login_is_rate_limited_and_secure_cookie_can_be_enabled(self):
        for _ in range(10):
            self.assertEqual(self.login('wrong-password').status_code, 401)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '900')
        with self.store.connect() as db:
            db.execute('DELETE FROM login_attempts')
        self.app.config['ADMIN_COOKIE_SECURE'] = True
        self.assertIn('Secure', self.login().headers['Set-Cookie'])

    def test_device_ingest_remains_separate_from_admin_session(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(self.client.post('/api/scd40').status_code, 200)
        with patch.dict('os.environ', {'SMARTOFFICE_DEVICE_TOKEN': 'device-test-only'}):
            self.assertEqual(self.client.post('/api/scd40').status_code, 401)
            self.assertEqual(self.client.post('/api/scd40', headers={'X-Device-Token': 'device-test-only'}).status_code, 200)


if __name__ == '__main__':
    unittest.main()
