"""Windows development stand with real providers and ML; runtime files stay ignored.

Run with .venv/local-runtime/python/Scripts/python.exe scripts/local_stand.py
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.venv/local-runtime'
LOGS = ROOT / 'logs/local'
CONFIG = RUNTIME / 'stand.json'


def short_path(path):
    # PostgreSQL's Windows binaries use narrow paths during initdb bootstrap.
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer)):
        raise OSError('Cannot resolve Windows short path')
    return Path(buffer.value)


def listening(port):
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def configuration():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding='utf-8'))
    value = {'db_password': secrets.token_urlsafe(24),
             'demo_email': 'demo@example.com', 'demo_password': secrets.token_urlsafe(15)}
    CONFIG.write_text(json.dumps(value, indent=2), encoding='utf-8')
    return value


def backend_environment():
    from dotenv import dotenv_values
    env = os.environ.copy()
    env.update({k: v for k, v in dotenv_values(ROOT / 'backend/.env.review').items() if v is not None})
    env.update({k: v for k, v in dotenv_values(ROOT / 'backend/.env').items() if v is not None})
    config = configuration()
    env.update(DEBUG='false', DATABASE_URL=(
        'postgresql+asyncpg://stylelink:' + config['db_password'] + '@127.0.0.1:5433/stylelink'),
        FASHION_CLIP_URL='http://127.0.0.1:8001', SIZE_SHIFT_URL='http://127.0.0.1:8001',
        FASHION_CLIP_TIMEOUT_SECONDS='300', PYTHONIOENCODING='utf-8')
    return env


async def prepare_database():
    import asyncpg
    config = configuration()
    connection = await asyncpg.connect(host='127.0.0.1', port=5433, user='stylelink',
                                     password=config['db_password'], database='postgres')
    try:
        exists = await connection.fetchval("SELECT 1 FROM pg_database WHERE datname='stylelink'")
        if not exists:
            await connection.execute('CREATE DATABASE stylelink')
    finally:
        await connection.close()
    sys.path.insert(0, str(ROOT / 'backend'))
    from app.models import Base, User, Profile
    from app.core.database import engine, AsyncSessionLocal
    from app.core.security import hash_password
    from sqlalchemy import select
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == config['demo_email']))
        if user is None:
            user = User(email=config['demo_email'], name='Local demo',
                        password_hash=hash_password(config['demo_password']))
            db.add(user)
            await db.flush()
            db.add(Profile(user_id=user.id))
            await db.commit()
    await engine.dispose()


def start_process(name, command, cwd, env):
    with (LOGS / (name + '.log')).open('a', encoding='utf-8') as output:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    (RUNTIME / (name + '.pid')).write_text(str(process.pid))
    print(name + ' started; PID=' + str(process.pid), flush=True)


def start():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    config = configuration()
    runtime_path = short_path(RUNTIME)
    pg = runtime_path / 'postgres/pgsql/bin'
    data = runtime_path / 'pgdata'
    if not (data / 'PG_VERSION').exists():
        if listening(5433):
            raise RuntimeError('Port 5433 is already occupied; refusing to use another database')
        password_file = runtime_path / 'pg-password.txt'
        password_file.write_text(config['db_password'], encoding='utf-8')
        with (LOGS / 'postgres-init.log').open('a') as output:
            subprocess.run([str(pg / 'initdb.exe'), '-D', str(data), '-U', 'stylelink',
                            '--pwfile=' + str(password_file), '-A', 'scram-sha-256',
                            '-E', 'UTF8', '--locale=C'], check=True, stdout=output, stderr=output)
    if not listening(5433):
        subprocess.run([str(pg / 'pg_ctl.exe'), '-D', str(data), '-l', str(short_path(LOGS) / 'postgres.log'),
                        '-o', '-h 127.0.0.1 -p 5433', '-w', 'start'], check=True)
    env = backend_environment()
    subprocess.run([sys.executable, str(Path(__file__).resolve()), '--prepare-db'],
                   cwd=ROOT / 'backend', env=env, check=True)
    if not listening(8001):
        ml_env = os.environ.copy()
        ml_env.update(PYTHONIOENCODING='utf-8', FIT_MODEL_BACKEND='b2',
                      B2_MODEL_PATH=str(ROOT / 'ml/models/B2_tfidf_logistic_regression.joblib'),
                      HF_HOME=str(runtime_path / 'huggingface'), HF_HUB_DISABLE_SYMLINKS_WARNING='1')
        start_process('ml', [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host',
                            '127.0.0.1', '--port', '8001'], ROOT / 'ml', ml_env)
    if not listening(8000):
        start_process('backend', [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host',
                                 '127.0.0.1', '--port', '8000'], ROOT / 'backend', env)
    if not listening(5173):
        node = shutil.which('node')
        if not node:
            candidates = list((Path(os.environ['LOCALAPPDATA']) / 'Microsoft/WinGet/Packages').glob(
                'OpenJS.NodeJS.LTS_*/node-*/node.exe'))
            node = str(candidates[0]) if candidates else None
        if not node:
            raise RuntimeError('Node.js is required')
        frontend_env = os.environ.copy()
        frontend_env['VITE_API_URL'] = 'http://127.0.0.1:8000'
        start_process('frontend', [node, 'node_modules/vite/bin/vite.js', '--host',
                                  '127.0.0.1', '--port', '5173', '--strictPort'],
                      ROOT / 'frontend', frontend_env)
    print('UI: http://localhost:5173 ; logs: ' + str(LOGS))
    print('Local login details: ' + str(CONFIG))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-db', action='store_true')
    args = parser.parse_args()
    if args.prepare_db:
        asyncio.run(prepare_database())
    else:
        start()
