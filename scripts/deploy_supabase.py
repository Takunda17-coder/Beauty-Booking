# -*- coding: utf-8 -*-
"""
Supabase Schema Deployment Script
Connects to the Supabase PostgreSQL database and executes the schema migration.
"""

import sys
import os
import argparse
import getpass
import psycopg2

DEFAULT_HOST = "db.caznldhgmetdcihrgkgk.supabase.co"
DEFAULT_IPV6_HOST = "2a05:d018:1701:d200:3ed0:5ba4:66d2:d248"
DEFAULT_PORT = 5432
DEFAULT_DBNAME = "postgres"
DEFAULT_USER = "postgres"

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
MIGRATION_FILE = os.path.join(root_dir, "supabase", "migrations", "20260903_beauty_booking_schema.sql")


def get_connection(password, host=DEFAULT_HOST, port=DEFAULT_PORT, dbname=DEFAULT_DBNAME, user=DEFAULT_USER):
    """Attempts connection using domain name, then IPv6 literal if DNS resolution fails."""
    hosts_to_try = [host, DEFAULT_IPV6_HOST]
    last_err = None

    for h in hosts_to_try:
        try:
            print(f"Connecting to Supabase PostgreSQL at {h}:{port}...")
            conn = psycopg2.connect(
                host=h,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                sslmode="require",
                connect_timeout=10,
            )
            print(f"✅ Successfully connected to {h}:{port}!")
            return conn
        except Exception as e:
            last_err = e
            print(f"Connection attempt to {h} failed: {e}")

    raise last_err


def deploy_schema(password):
    if not os.path.exists(MIGRATION_FILE):
        print(f"❌ Migration file not found: {MIGRATION_FILE}")
        sys.exit(1)

    with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print(f"📄 Loaded SQL schema from {os.path.basename(MIGRATION_FILE)} ({len(sql_content)} bytes)")

    conn = get_connection(password)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        print("⏳ Executing schema migration...")
        cursor.execute(sql_content)
        print("✅ Schema executed successfully!")

        print("\n🔍 Verifying created tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found public tables ({len(tables)}):")
        for t in tables:
            print(f"  • {t}")

        print("\n🔍 Verifying Row-Level Security (RLS) policies...")
        cursor.execute("""
            SELECT tablename, policyname 
            FROM pg_policies 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """)
        policies = cursor.fetchall()
        for tablename, policyname in policies:
            print(f"  • {tablename}: {policyname}")

        print("\n🎉 Supabase Free Tier Schema Migration is 100% COMPLETE!")
    except Exception as e:
        print(f"❌ Error during migration: {e}")
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Deploy Beauty Booking schema to Supabase")
    parser.add_argument("--password", "-p", help="Database password (or via SUPABASE_DB_PASSWORD env var)")
    args = parser.parse_args()

    password = args.password or os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        password = getpass.getpass("Enter your Supabase database password: ")

    deploy_schema(password)


if __name__ == "__main__":
    main()
