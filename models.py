import os
import json
from datetime import datetime, timezone
import uuid
import logging
import threading
from contextlib import contextmanager

from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json

load_dotenv()
logger = logging.getLogger(__name__)

_store_lock = threading.RLock()

_MEMORY_STORE = {
    "users": {},
    "uploads": {},
    "reports": {},
    "presentation_sessions": {},
    "historical_reports": {},
}

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
_db_pool = None
_use_postgres = False

def _init_postgres():
    global _db_pool, _use_postgres
    if not DATABASE_URL:
        print("[DB WARN] DATABASE_URL not set. Operating with in-memory store.")
        _use_postgres = False
        return

    try:
        _db_pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
        _use_postgres = True
        print("[DB OK] Connected to Neon PostgreSQL Database Pool")
        _create_tables()
    except Exception as e:
        print(f"[DB WARN] PostgreSQL connection error: {e}. Fallback to in-memory store active.")
        _use_postgres = False

def _create_tables():
    if not _use_postgres or _db_pool is None:
        return
    conn = None
    try:
        conn = _db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(64) PRIMARY KEY,
                uid VARCHAR(64),
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE NOT NULL,
                photo_url TEXT,
                provider VARCHAR(50) DEFAULT 'password',
                password_hash TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

            CREATE TABLE IF NOT EXISTS uploads (
                id VARCHAR(64) PRIMARY KEY,
                filename VARCHAR(500),
                mime_type VARCHAR(100),
                file_path TEXT,
                user_id VARCHAR(64),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);

            CREATE TABLE IF NOT EXISTS reports (
                id VARCHAR(64) PRIMARY KEY,
                report_json JSONB,
                report_type VARCHAR(50),
                user_id VARCHAR(64),
                upload_id VARCHAR(64),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);

            CREATE TABLE IF NOT EXISTS presentation_sessions (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64),
                topic VARCHAR(255),
                status VARCHAR(50),
                started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                metrics JSONB
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON presentation_sessions(user_id);

            CREATE TABLE IF NOT EXISTS historical_reports (
                id VARCHAR(64) PRIMARY KEY,
                session_id VARCHAR(64),
                user_id VARCHAR(64),
                topic VARCHAR(255),
                report_json JSONB,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_historical_user_topic ON historical_reports(user_id, topic);
            """)
        conn.commit()
        print("[DB OK] PostgreSQL tables and indexes verified successfully")
    except Exception as e:
        logger.error(f"[DB ERR] Error creating tables: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            _db_pool.putconn(conn)

@contextmanager
def get_db():
    global _use_postgres
    if not _use_postgres or _db_pool is None:
        yield None
        return

    conn = None
    try:
        conn = _db_pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.warning(f"[DB ERROR] PostgreSQL query failed ({e}). Fallback active.")
        raise
    finally:
        if conn:
            _db_pool.putconn(conn)

class CompatDB:
    def __init__(self):
        self.is_connected = True
db = CompatDB()

_init_postgres()

def _serialize_dt(dt):
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt) if dt else None

def _parse_dt(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            pass
    return datetime.now(timezone.utc)

class User:
    def __init__(self, id, uid=None, name="", email="", photo_url=None, provider="password", password_hash=None, created_at=None, updated_at=None):
        self.id = str(id)
        self.uid = str(uid or id)
        self.name = name or ""
        self.email = email or ""
        self.photo_url = photo_url
        self.provider = provider or "password"
        self.password_hash = password_hash
        self.created_at = _parse_dt(created_at)
        self.updated_at = _parse_dt(updated_at)

    @staticmethod
    def get_by_email(email: str):
        email = email.lower().strip()
        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute(
                                "SELECT id, uid, name, email, photo_url, provider, password_hash, created_at, updated_at FROM users WHERE email = %s LIMIT 1",
                                (email,)
                            )
                            row = cur.fetchone()
                            if row:
                                return User(
                                    id=row["id"], uid=row.get("uid") or row["id"],
                                    name=row.get("name"), email=row.get("email"),
                                    photo_url=row.get("photo_url"), provider=row.get("provider", "password"),
                                    password_hash=row.get("password_hash"),
                                    created_at=row.get("created_at"), updated_at=row.get("updated_at")
                                )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on User.get_by_email: {e}")

        with _store_lock:
            for u in _MEMORY_STORE["users"].values():
                if u.get("email") == email:
                    return User(
                        id=u.get("id"), uid=u.get("uid") or u.get("id"),
                        name=u.get("name"), email=u.get("email"),
                        photo_url=u.get("photo_url"), provider=u.get("provider", "password"),
                        password_hash=u.get("password_hash"),
                        created_at=u.get("created_at"), updated_at=u.get("updated_at")
                    )
        return None

    @staticmethod
    def get_by_id(user_id: str):
        user_id = str(user_id)
        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute(
                                "SELECT id, uid, name, email, photo_url, provider, password_hash, created_at, updated_at FROM users WHERE id = %s LIMIT 1",
                                (user_id,)
                            )
                            row = cur.fetchone()
                            if row:
                                return User(
                                    id=row["id"], uid=row.get("uid") or row["id"],
                                    name=row.get("name"), email=row.get("email"),
                                    photo_url=row.get("photo_url"), provider=row.get("provider", "password"),
                                    password_hash=row.get("password_hash"),
                                    created_at=row.get("created_at"), updated_at=row.get("updated_at")
                                )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on User.get_by_id: {e}")

        with _store_lock:
            u = _MEMORY_STORE["users"].get(user_id)
            if u:
                return User(
                    id=u.get("id"), uid=u.get("uid") or u.get("id"),
                    name=u.get("name"), email=u.get("email"),
                    photo_url=u.get("photo_url"), provider=u.get("provider", "password"),
                    password_hash=u.get("password_hash"),
                    created_at=u.get("created_at"), updated_at=u.get("updated_at")
                )
        return None

    @staticmethod
    def create(name: str, email: str, photo_url: str = None, provider: str = "password", password_hash: str = None):
        user_id = str(uuid.uuid4())
        return User.create_with_id(user_id, name, email, photo_url, provider, password_hash)

    @staticmethod
    def create_with_id(user_id: str, name: str, email: str, photo_url: str = None, provider: str = "password", password_hash: str = None):
        user_id = str(user_id)
        now = datetime.now(timezone.utc)
        clean_name = name.strip() if name else ""
        clean_email = email.lower().strip() if email else ""

        doc = {
            "id": user_id,
            "uid": user_id,
            "name": clean_name,
            "email": clean_email,
            "photo_url": photo_url,
            "provider": provider or "password",
            "password_hash": password_hash,
            "created_at": now,
            "updated_at": now,
        }
        with _store_lock:
            _MEMORY_STORE["users"][user_id] = doc

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO users (id, uid, name, email, photo_url, provider, password_hash, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (email) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    photo_url = EXCLUDED.photo_url,
                                    password_hash = COALESCE(EXCLUDED.password_hash, users.password_hash),
                                    updated_at = EXCLUDED.updated_at
                                RETURNING id
                                """,
                                (user_id, user_id, clean_name, clean_email, photo_url, provider, password_hash, now, now)
                            )
                            res = cur.fetchone()
                            if res:
                                user_id = str(res[0])
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on User.create_with_id: {e}")

        return User(
            id=user_id, uid=user_id, name=clean_name, email=clean_email,
            photo_url=photo_url, provider=provider, password_hash=password_hash,
            created_at=now, updated_at=now
        )

    def to_dict(self):
        return {
            "id": self.id,
            "uid": self.uid,
            "name": self.name,
            "email": self.email,
            "photo_url": self.photo_url,
            "provider": self.provider,
            "created_at": _serialize_dt(self.created_at),
            "updated_at": _serialize_dt(self.updated_at),
        }

class Upload:
    def __init__(self, id, filename, mime_type, file_path, user_id, created_at=None):
        self.id = str(id)
        self.filename = filename
        self.mime_type = mime_type
        self.file_path = file_path
        self.user_id = str(user_id) if user_id else ""
        self.created_at = _parse_dt(created_at)

    @staticmethod
    def create(filename: str, mime_type: str, file_path: str, user_id: str):
        upload_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_id_str = str(user_id) if user_id else ""

        doc = {
            "id": upload_id,
            "filename": filename,
            "mime_type": mime_type,
            "file_path": file_path,
            "user_id": user_id_str,
            "created_at": now,
        }
        with _store_lock:
            _MEMORY_STORE["uploads"][upload_id] = doc

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO uploads (id, filename, mime_type, file_path, user_id, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (upload_id, filename, mime_type, file_path, user_id_str, now)
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on Upload.create: {e}")

        return Upload(
            id=upload_id, filename=filename, mime_type=mime_type,
            file_path=file_path, user_id=user_id_str, created_at=now
        )

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "user_id": self.user_id,
            "created_at": _serialize_dt(self.created_at),
        }

class Report:
    def __init__(self, id, report_json, report_type, user_id, upload_id=None, created_at=None, updated_at=None):
        self.id = str(id)
        self.report_json = report_json or {}
        self.report_type = report_type or ""
        self.user_id = str(user_id) if user_id else ""
        self.upload_id = str(upload_id) if upload_id else None
        self.created_at = _parse_dt(created_at)
        self.updated_at = _parse_dt(updated_at)

    @staticmethod
    def create(report_json: dict, report_type: str, user_id: str, upload_id: str = None):
        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_id_str = str(user_id) if user_id else ""
        upload_id_str = str(upload_id) if upload_id else None

        doc = {
            "id": report_id,
            "report_json": report_json,
            "report_type": report_type,
            "user_id": user_id_str,
            "upload_id": upload_id_str,
            "created_at": now,
            "updated_at": now,
        }
        with _store_lock:
            _MEMORY_STORE["reports"][report_id] = doc

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO reports (id, report_json, report_type, user_id, upload_id, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """,
                                (report_id, Json(report_json), report_type, user_id_str, upload_id_str, now, now)
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on Report.create: {e}")

        return Report(
            id=report_id, report_json=report_json, report_type=report_type,
            user_id=user_id_str, upload_id=upload_id_str, created_at=now, updated_at=now
        )

    @staticmethod
    def get_by_user(user_id: str):
        user_id_str = str(user_id) if user_id else ""
        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute(
                                "SELECT id, report_json, report_type, user_id, upload_id, created_at, updated_at FROM reports WHERE user_id = %s ORDER BY created_at DESC",
                                (user_id_str,)
                            )
                            rows = cur.fetchall()
                            reports = []
                            for row in rows:
                                reports.append(Report(
                                    id=row["id"], report_json=row.get("report_json"),
                                    report_type=row.get("report_type"), user_id=row.get("user_id"),
                                    upload_id=row.get("upload_id"), created_at=row.get("created_at"),
                                    updated_at=row.get("updated_at")
                                ))
                            return reports
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on Report.get_by_user: {e}")

        reports = []
        with _store_lock:
            for r in _MEMORY_STORE["reports"].values():
                if r.get("user_id") == user_id_str:
                    reports.append(Report(
                        id=r.get("id"), report_json=r.get("report_json"),
                        report_type=r.get("report_type"), user_id=r.get("user_id"),
                        upload_id=r.get("upload_id"), created_at=r.get("created_at"),
                        updated_at=r.get("updated_at")
                    ))
        return sorted(reports, key=lambda x: str(x.created_at), reverse=True)

    def to_dict(self):
        return {
            "id": self.id,
            "report_type": self.report_type,
            "report_json": self.report_json,
            "user_id": self.user_id,
            "upload_id": self.upload_id,
            "created_at": _serialize_dt(self.created_at),
        }

class PresentationSession:
    def __init__(self, id, user_id, topic, status, started_at=None, ended_at=None, metrics=None):
        self.id = str(id)
        self.user_id = str(user_id) if user_id else ""
        self.topic = topic or ""
        self.status = status or "STREAMING"
        self.started_at = _parse_dt(started_at)
        self.ended_at = _parse_dt(ended_at)
        self.metrics = metrics or {
            "eye_contact_scores": [],
            "posture_scores": [],
            "wpm_history": [],
            "fillers_detected": 0,
            "transcripts": [],
            "interruptions": [],
            "confidence_scores": [],
            "vocal_sentiment_scores": [],
        }

    @staticmethod
    def create(user_id: str, topic: str):
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        user_id_str = str(user_id) if user_id else ""
        default_metrics = {
            "eye_contact_scores": [],
            "posture_scores": [],
            "wpm_history": [],
            "fillers_detected": 0,
            "transcripts": [],
            "interruptions": [],
            "confidence_scores": [],
            "vocal_sentiment_scores": [],
        }
        doc = {
            "id": session_id,
            "user_id": user_id_str,
            "topic": topic,
            "status": "STREAMING",
            "started_at": now,
            "ended_at": now,
            "metrics": default_metrics,
        }
        with _store_lock:
            _MEMORY_STORE["presentation_sessions"][session_id] = doc

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO presentation_sessions (id, user_id, topic, status, started_at, ended_at, metrics)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """,
                                (session_id, user_id_str, topic, "STREAMING", now, now, Json(default_metrics))
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on PresentationSession.create: {e}")

        return PresentationSession(
            id=session_id, user_id=user_id_str, topic=topic,
            status="STREAMING", started_at=now, ended_at=now, metrics=default_metrics
        )

    @staticmethod
    def get_by_id(session_id: str):
        session_id_str = str(session_id)
        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute(
                                "SELECT id, user_id, topic, status, started_at, ended_at, metrics FROM presentation_sessions WHERE id = %s LIMIT 1",
                                (session_id_str,)
                            )
                            row = cur.fetchone()
                            if row:
                                return PresentationSession(
                                    id=row["id"], user_id=row.get("user_id"),
                                    topic=row.get("topic"), status=row.get("status"),
                                    started_at=row.get("started_at"), ended_at=row.get("ended_at"),
                                    metrics=row.get("metrics")
                                )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on PresentationSession.get_by_id: {e}")

        with _store_lock:
            s = _MEMORY_STORE["presentation_sessions"].get(session_id_str)
            if s:
                return PresentationSession(
                    id=s.get("id"), user_id=s.get("user_id"),
                    topic=s.get("topic"), status=s.get("status"),
                    started_at=s.get("started_at"), ended_at=s.get("ended_at"),
                    metrics=s.get("metrics")
                )
        return None

    def update_metrics(self, key: str, value):
        if self.metrics and key in self.metrics:
            if isinstance(self.metrics[key], list):
                self.metrics[key].append(value)

        with _store_lock:
            if self.id in _MEMORY_STORE["presentation_sessions"]:
                _MEMORY_STORE["presentation_sessions"][self.id]["metrics"] = self.metrics

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE presentation_sessions SET metrics = %s WHERE id = %s",
                                (Json(self.metrics), self.id)
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres update_metrics error: {e}")

    def increment_metric(self, key: str, val: int = 1):
        if self.metrics and key in self.metrics:
            self.metrics[key] = self.metrics.get(key, 0) + val

        with _store_lock:
            if self.id in _MEMORY_STORE["presentation_sessions"]:
                _MEMORY_STORE["presentation_sessions"][self.id]["metrics"] = self.metrics

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE presentation_sessions SET metrics = %s WHERE id = %s",
                                (Json(self.metrics), self.id)
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres increment_metric error: {e}")

    def update_status(self, new_status: str):
        self.status = new_status
        now = datetime.now(timezone.utc)
        self.ended_at = now

        with _store_lock:
            if self.id in _MEMORY_STORE["presentation_sessions"]:
                _MEMORY_STORE["presentation_sessions"][self.id]["status"] = new_status
                _MEMORY_STORE["presentation_sessions"][self.id]["ended_at"] = now

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE presentation_sessions SET status = %s, ended_at = %s WHERE id = %s",
                                (new_status, now, self.id)
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres update_status error: {e}")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic": self.topic,
            "status": self.status,
            "started_at": _serialize_dt(self.started_at),
            "ended_at": _serialize_dt(self.ended_at),
            "metrics": self.metrics,
        }

class HistoricalReport:
    def __init__(self, id, session_id, user_id, topic, report_json, created_at=None):
        self.id = str(id)
        self.session_id = str(session_id) if session_id else ""
        self.user_id = str(user_id) if user_id else ""
        self.topic = topic or ""
        self.report_json = report_json or {}
        self.created_at = _parse_dt(created_at)

    @staticmethod
    def create(session_id: str, user_id: str, topic: str, report_json: dict):
        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        clean_topic = topic.strip().lower() if topic else ""
        user_id_str = str(user_id) if user_id else ""
        session_id_str = str(session_id) if session_id else ""

        doc = {
            "id": report_id,
            "session_id": session_id_str,
            "user_id": user_id_str,
            "topic": clean_topic,
            "report_json": report_json,
            "created_at": now,
        }
        with _store_lock:
            _MEMORY_STORE["historical_reports"][report_id] = doc

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO historical_reports (id, session_id, user_id, topic, report_json, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (report_id, session_id_str, user_id_str, clean_topic, Json(report_json), now)
                            )
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on HistoricalReport.create: {e}")

        return HistoricalReport(
            id=report_id, session_id=session_id_str, user_id=user_id_str,
            topic=topic, report_json=report_json, created_at=now
        )

    @staticmethod
    def get_by_user_and_topic(user_id: str, topic: str):
        topic_lower = topic.strip().lower() if topic else ""
        user_id_str = str(user_id) if user_id else ""

        if _use_postgres:
            try:
                with get_db() as conn:
                    if conn:
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            cur.execute(
                                "SELECT id, session_id, user_id, topic, report_json, created_at FROM historical_reports WHERE user_id = %s AND LOWER(topic) = %s ORDER BY created_at DESC",
                                (user_id_str, topic_lower)
                            )
                            rows = cur.fetchall()
                            reports = []
                            for row in rows:
                                reports.append(HistoricalReport(
                                    id=row["id"], session_id=row.get("session_id"),
                                    user_id=row.get("user_id"), topic=row.get("topic"),
                                    report_json=row.get("report_json"), created_at=row.get("created_at")
                                ))
                            return reports
            except Exception as e:
                logger.warning(f"[DB FALLBACK] Postgres error on get_by_user_and_topic: {e}")

        reports = []
        with _store_lock:
            for hr in _MEMORY_STORE["historical_reports"].values():
                if hr.get("user_id") == user_id_str and hr.get("topic") == topic_lower:
                    reports.append(HistoricalReport(
                        id=hr.get("id"), session_id=hr.get("session_id"),
                        user_id=hr.get("user_id"), topic=hr.get("topic"),
                        report_json=hr.get("report_json"), created_at=hr.get("created_at")
                    ))
        return sorted(reports, key=lambda x: str(x.created_at), reverse=True)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "topic": self.topic,
            "report_json": self.report_json,
            "created_at": _serialize_dt(self.created_at),
        }
