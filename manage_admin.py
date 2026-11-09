"""Create or reset an admin locally without starting YOLO or any devices."""
import getpass
import os
from pathlib import Path
from admin_auth import AdminStore


def main():
    print('Smart Office — siapkan akun admin lokal')
    username = input('Nama pengguna [admin]: ').strip() or 'admin'
    password = getpass.getpass('Kata sandi (12–128 karakter): ')
    confirmation = getpass.getpass('Ulangi kata sandi: ')
    if password != confirmation:
        raise ValueError('Konfirmasi kata sandi tidak cocok. Akun tidak diubah.')
    store = AdminStore(os.environ.get('SMARTOFFICE_AUTH_DB', str(Path(__file__).resolve().parent / 'instance' / 'admin_auth.db')))
    store.set_admin(username, password)
    print('Akun admin tersimpan. Sesi lama akun ini dicabut. Buka http://127.0.0.1:3000/login untuk masuk.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyboardInterrupt, EOFError) as error:
        print(str(error) or 'Dibatalkan.')
        raise SystemExit(1)
