from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS working_days (
  date TEXT PRIMARY KEY,                 -- YYYY-MM-DD
  is_open INTEGER NOT NULL DEFAULT 1     -- 1=open, 0=closed
);

CREATE TABLE IF NOT EXISTS time_slots (
  date TEXT NOT NULL,                    -- YYYY-MM-DD
  time TEXT NOT NULL,                    -- HH:MM
  is_enabled INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (date, time),
  FOREIGN KEY (date) REFERENCES working_days(date) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  username TEXT,
  date TEXT NOT NULL,                    -- YYYY-MM-DD
  time TEXT NOT NULL,                    -- HH:MM
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', -- active/cancelled
  created_at TEXT NOT NULL,              -- ISO
  cancelled_at TEXT,
  UNIQUE(date, time),
  FOREIGN KEY (date, time) REFERENCES time_slots(date, time) ON DELETE RESTRICT
);

-- Reminder jobs persistency (to restore after restart)
CREATE TABLE IF NOT EXISTS reminders (
  booking_id INTEGER PRIMARY KEY,
  job_id TEXT NOT NULL UNIQUE,
  run_at TEXT NOT NULL,                  -- ISO
  FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_status ON bookings(user_id, status);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);
"""

