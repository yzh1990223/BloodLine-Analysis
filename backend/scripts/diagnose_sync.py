#!/usr/bin/env python3
"""Diagnose lineage sync issues on deployment server."""

import sys
import os

# Adjust path for deployment
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, "..", "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from bloodline_api.db import SessionLocal
from bloodline_api.models import Edge
from bloodline_api.services.lineage_exporter import sync_lineage_to_mysql


def main():
    # 1. Check SQLite data
    sqlite_db = SessionLocal()
    count = sqlite_db.query(Edge).filter(Edge.type == "FLOWS_TO").count()
    print(f"SQLite FLOWS_TO edges: {count}")

    # 2. Check MySQL connection and table schema
    mysql_dsn = "mysql+pymysql://root:root@127.0.0.1:3306/DM"
    mysql_engine = create_engine(mysql_dsn, future=True, pool_pre_ping=True)
    MySQLSession = sessionmaker(bind=mysql_engine)
    mysql_db = MySQLSession()

    try:
        mysql_db.execute(text("SELECT 1"))
        print("MySQL connection: OK")

        result = mysql_db.execute(text("SHOW TABLES LIKE 't_relationship'"))
        if result.fetchone():
            print("Table t_relationship: EXISTS")
            result = mysql_db.execute(text("""
                SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'DM' AND TABLE_NAME = 't_relationship'
                AND COLUMN_NAME IN ('src_obj_enname', 'tgt_obj_enname')
            """))
            for row in result:
                print(f"  {row[0]}: VARCHAR({row[1]})")
        else:
            print("Table t_relationship: NOT EXISTS")
    except Exception as e:
        print(f"MySQL ERROR: {type(e).__name__}: {e}")
        return
    finally:
        mysql_db.close()

    # 3. Try sync
    try:
        result = sync_lineage_to_mysql(sqlite_db, mysql_dsn)
        print(f"Sync result: {result}")
    except Exception as e:
        print(f"Sync ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
