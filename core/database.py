"""
数据库适配层
本地开发使用 SQLite，云端部署可切换为 PostgreSQL (Supabase)
对外暴露统一接口，上层代码无需关心底层实现。

修复审查报告指出的 database.py:28 事务处理不一致问题：
- 所有写操作统一使用 try/except + commit/rollback
- SQLite 连接使用 WAL 模式提升并发性能
"""
import sqlite3
import os
import uuid
import logging
import threading
from datetime import datetime

import streamlit as st

from core.config import DB_PATH

logger = logging.getLogger(__name__)

# SQLite 线程锁（SQLite 不支持真正的并发写入）
_sqlite_lock = threading.Lock()


def _get_db_type():
    """判断应使用的数据库类型"""
    try:
        secrets = st.secrets
        if "database" in secrets and secrets["database"].get("type") == "postgresql":
            return "postgresql"
    except Exception:
        pass
    return "sqlite"


@st.cache_resource
def get_connection():
    """获取数据库连接（进程级缓存）"""
    db_type = _get_db_type()

    if db_type == "postgresql":
        import psycopg2
        cfg = st.secrets["database"]
        conn = psycopg2.connect(
            host=cfg["host"],
            port=cfg.get("port", 5432),
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=cfg["password"],
        )
        conn.autocommit = True
        return conn
    else:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # 启用 WAL 模式提升并发读性能
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn


def _ph():
    """返回对应数据库的占位符"""
    if _get_db_type() == "postgresql":
        return "%s"
    return "?"


def _safe_commit(conn):
    """安全提交事务（仅 SQLite 需要显式 commit）"""
    if _get_db_type() == "sqlite":
        try:
            conn.commit()
        except Exception as e:
            logger.error("事务提交失败: %s", e)
            try:
                conn.rollback()
            except Exception:
                pass
            raise


def init_db():
    """初始化数据库表结构（幂等操作）"""
    conn = get_connection()
    with _sqlite_lock:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    filename TEXT,
                    file_size_mb REAL,
                    image_width INTEGER,
                    image_height INTEGER,
                    crs_original TEXT,
                    resolution_m REAL,
                    bamboo_pixels INTEGER,
                    total_pixels INTEGER,
                    bamboo_area_ha REAL,
                    coverage_pct REAL,
                    bbox_wgs84 TEXT,
                    model_version TEXT,
                    processing_time_s REAL,
                    status TEXT DEFAULT 'success'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_logs (
                    id TEXT PRIMARY KEY,
                    record_id TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    location_desc TEXT,
                    center_lat REAL,
                    center_lon REAL,
                    affected_area_ha REAL,
                    confidence REAL,
                    suggested_action TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    alert_id TEXT,
                    task_desc TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'normal',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)
            _safe_commit(conn)
        except Exception as e:
            logger.error("数据库初始化失败: %s", e)
            raise


def save_analysis_record(record: dict) -> str:
    """保存分析记录，返回记录ID"""
    conn = get_connection()
    ph = _ph()
    record_id = record.get("id", str(uuid.uuid4()))
    created_at = record.get("created_at", datetime.now().isoformat())

    with _sqlite_lock:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO analysis_records "
                "(id, created_at, filename, file_size_mb, image_width, image_height, "
                "crs_original, resolution_m, bamboo_pixels, total_pixels, "
                "bamboo_area_ha, coverage_pct, bbox_wgs84, model_version, "
                "processing_time_s, status) "
                "VALUES ({})".format(",".join([ph] * 16)),
                (
                    record_id, created_at,
                    record.get("filename"), record.get("file_size_mb"),
                    record.get("image_width"), record.get("image_height"),
                    record.get("crs_original"), record.get("resolution_m"),
                    record.get("bamboo_pixels"), record.get("total_pixels"),
                    record.get("bamboo_area_ha"), record.get("coverage_pct"),
                    record.get("bbox_wgs84"), record.get("model_version"),
                    record.get("processing_time_s"), record.get("status", "success"),
                ),
            )
            _safe_commit(conn)
        except Exception as e:
            logger.error("保存分析记录失败: %s", e)
            raise

    return record_id


def save_alert(alert: dict) -> str:
    """保存单条预警日志"""
    conn = get_connection()
    ph = _ph()
    alert_id = alert.get("id", str(uuid.uuid4()))
    created_at = alert.get("created_at", datetime.now().isoformat())

    with _sqlite_lock:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO alert_logs "
                "(id, record_id, alert_type, severity, location_desc, "
                "center_lat, center_lon, affected_area_ha, confidence, "
                "suggested_action, created_at) "
                "VALUES ({})".format(",".join([ph] * 11)),
                (
                    alert_id, alert.get("record_id"),
                    alert.get("alert_type"), alert.get("severity"),
                    alert.get("location_desc"),
                    alert.get("center_lat"), alert.get("center_lon"),
                    alert.get("affected_area_ha"), alert.get("confidence"),
                    alert.get("suggested_action"), created_at,
                ),
            )
            _safe_commit(conn)
        except Exception as e:
            logger.error("保存预警日志失败: %s", e)
            raise

    return alert_id


def save_alerts(alerts: list) -> list:
    """批量保存预警日志"""
    return [save_alert(a) for a in alerts]


def save_task(task: dict) -> str:
    """保存任务"""
    conn = get_connection()
    ph = _ph()
    task_id = task.get("id", str(uuid.uuid4()))
    now = datetime.now().isoformat()

    with _sqlite_lock:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO tasks "
                "(id, alert_id, task_desc, status, priority, created_at, updated_at, notes) "
                "VALUES ({})".format(",".join([ph] * 8)),
                (
                    task_id, task.get("alert_id"),
                    task.get("task_desc"), task.get("status", "pending"),
                    task.get("priority", "normal"),
                    task.get("created_at", now), now,
                    task.get("notes", ""),
                ),
            )
            _safe_commit(conn)
        except Exception as e:
            logger.error("保存任务失败: %s", e)
            raise

    return task_id


def update_task_status(task_id: str, status: str, notes: str = None):
    """更新任务状态"""
    conn = get_connection()
    ph = _ph()
    now = datetime.now().isoformat()

    with _sqlite_lock:
        cursor = conn.cursor()
        try:
            if notes is not None:
                cursor.execute(
                    "UPDATE tasks SET status={ph}, updated_at={ph}, notes={ph} WHERE id={ph}".format(ph=ph),
                    (status, now, notes, task_id),
                )
            else:
                cursor.execute(
                    "UPDATE tasks SET status={ph}, updated_at={ph} WHERE id={ph}".format(ph=ph),
                    (status, now, task_id),
                )
            _safe_commit(conn)
        except Exception as e:
            logger.error("更新任务状态失败: %s", e)
            raise


def get_analysis_history(limit=50, offset=0) -> list:
    """获取历史分析记录"""
    conn = get_connection()
    ph = _ph()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM analysis_records ORDER BY created_at DESC LIMIT {} OFFSET {}".format(ph, ph),
        (limit, offset),
    )
    rows = cursor.fetchall()

    if _get_db_type() == "sqlite":
        return [dict(row) for row in rows]
    else:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


def get_alerts(record_id=None, limit=50) -> list:
    """获取预警日志"""
    conn = get_connection()
    ph = _ph()
    cursor = conn.cursor()

    if record_id:
        cursor.execute(
            "SELECT * FROM alert_logs WHERE record_id={} ORDER BY created_at DESC LIMIT {}".format(ph, ph),
            (record_id, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM alert_logs ORDER BY created_at DESC LIMIT {}".format(ph),
            (limit,),
        )

    rows = cursor.fetchall()
    if _get_db_type() == "sqlite":
        return [dict(row) for row in rows]
    else:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


def get_tasks(status=None, limit=50) -> list:
    """获取任务列表"""
    conn = get_connection()
    ph = _ph()
    cursor = conn.cursor()

    if status:
        cursor.execute(
            "SELECT t.*, a.location_desc, a.severity as alert_severity "
            "FROM tasks t LEFT JOIN alert_logs a ON t.alert_id = a.id "
            "WHERE t.status={} ORDER BY t.created_at DESC LIMIT {}".format(ph, ph),
            (status, limit),
        )
    else:
        cursor.execute(
            "SELECT t.*, a.location_desc, a.severity as alert_severity "
            "FROM tasks t LEFT JOIN alert_logs a ON t.alert_id = a.id "
            "ORDER BY t.created_at DESC LIMIT {}".format(ph),
            (limit,),
        )

    rows = cursor.fetchall()
    if _get_db_type() == "sqlite":
        return [dict(row) for row in rows]
    else:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


def get_dashboard_stats() -> dict:
    """获取驾驶舱汇总统计"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analysis_records WHERE status='success'")
    total_analyses = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM analysis_records WHERE status='success' ORDER BY created_at DESC LIMIT 1")
    latest = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM alert_logs")
    total_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'")
    pending_tasks = cursor.fetchone()[0]

    return {
        "total_analyses": total_analyses,
        "total_alerts": total_alerts,
        "pending_tasks": pending_tasks,
        "latest_record": dict(latest) if latest else None,
    }


def get_yearly_bamboo_area() -> list:
    """
    获取数据库中实际存在的年份和竹林面积数据
    基于真实的分析记录，按年份汇总
    
    Returns:
        list: [{'year': int, 'area_ha': float}, ...] 按年份排序
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 从分析记录中提取年份和竹林面积
    # 使用strftime提取年份（SQLite语法）
    cursor.execute("""
        SELECT 
            CAST(strftime('%Y', created_at) AS INTEGER) as year,
            AVG(bamboo_area_ha) as avg_area_ha,
            COUNT(*) as record_count
        FROM analysis_records 
        WHERE status='success' AND bamboo_area_ha IS NOT NULL
        GROUP BY strftime('%Y', created_at)
        ORDER BY year ASC
    """)
    
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        year, avg_area_ha, record_count = row
        if year is not None and avg_area_ha is not None:
            result.append({
                'year': int(year),
                'area_ha': round(float(avg_area_ha), 2),
                'record_count': int(record_count)
            })
    
    return result
