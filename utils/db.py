import sqlite3
import os

DB_PATH = "tiertest.db"

OWNER_ID = 253335267618848778

TIERS = ["HT1", "HT2", "HT3", "LT1", "LT2", "LT3", "LT4", "LT5"]

TIER_COLORS = {
    "HT1": 0xFFD700,  # Gold
    "HT2": 0xFFA500,  # Orange
    "HT3": 0xFF6347,  # Tomato
    "LT1": 0x1E90FF,  # Dodger Blue
    "LT2": 0x00BFFF,  # Deep Sky Blue
    "LT3": 0x7B68EE,  # Medium Slate Blue
    "LT4": 0x9370DB,  # Medium Purple
    "LT5": 0xC0C0C0,  # Silver
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            guild_id TEXT PRIMARY KEY,
            panel_channel_id TEXT,
            results_channel_id TEXT,
            appeals_channel_id TEXT,
            ticket_category_id TEXT,
            queue_channel_id TEXT,
            sa_tester_role_id TEXT,
            as_tester_role_id TEXT,
            tested_role_id TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tier_roles (
            guild_id TEXT,
            tier TEXT,
            role_id TEXT,
            PRIMARY KEY (guild_id, tier)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            ign TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'waiting'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            channel_id TEXT,
            user_id TEXT,
            tester_id TEXT,
            ign TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            ign TEXT,
            tier TEXT,
            tester_id TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            ign TEXT,
            current_tier TEXT,
            reason TEXT,
            channel_id TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            guild_id TEXT,
            user_id TEXT,
            reason TEXT,
            banned_by TEXT,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    conn.commit()
    conn.close()

def get_config(guild_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM config WHERE guild_id = ?", (str(guild_id),)).fetchone()
    conn.close()
    return dict(row) if row else None

def is_sa_tester(member, config):
    if config and config["sa_tester_role_id"]:
        role = member.guild.get_role(int(config["sa_tester_role_id"]))
        if role and role in member.roles:
            return True
    return False

def is_as_tester(member, config):
    if config and config["as_tester_role_id"]:
        role = member.guild.get_role(int(config["as_tester_role_id"]))
        if role and role in member.roles:
            return True
    return False

def is_any_tester(member, config):
    return is_sa_tester(member, config) or is_as_tester(member, config)

init_db()
