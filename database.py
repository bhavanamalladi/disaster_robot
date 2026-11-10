
"""
Edge Cloud - Local Database Manager

Manages:
1. LiDAR observations
2. Robot status
3. Search tasks
4. Mission information
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# Database file location
DATABASE_PATH = Path.home() / "edge_cloud" / "data" / "edge_cloud.db"


def get_timestamp():
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def initialize_database():
    """Create all required database tables if they do not exist."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:

        # 1. LiDAR observations
        connection.execute("""
            CREATE TABLE IF NOT EXISTS lidar_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                robot_id TEXT NOT NULL,
                total_measurements INTEGER NOT NULL,
                valid_measurements INTEGER NOT NULL,
                nearest_distance REAL
            )
        """)

        # 2. Robot status
        connection.execute("""
            CREATE TABLE IF NOT EXISTS robot_status (
                robot_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                current_task_id INTEGER,
                FOREIGN KEY (current_task_id)
                    REFERENCES search_tasks(task_id)
            )
        """)

        # 3. Missions
        connection.execute("""
            CREATE TABLE IF NOT EXISTS missions (
                mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL
            )
        """)

        # 4. Search tasks
        connection.execute("""
            CREATE TABLE IF NOT EXISTS search_tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id INTEGER NOT NULL,
                robot_id TEXT,
                search_zone TEXT NOT NULL,
                task_description TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (mission_id)
                    REFERENCES missions(mission_id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS robot_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            )
        """)

    print(f"Database ready: {DATABASE_PATH}")


# --------------------------------------------------
# LIDAR OBSERVATION MANAGEMENT
# --------------------------------------------------

def save_lidar_observation(
    robot_id,
    total_measurements,
    valid_measurements,
    nearest_distance
):
    """Save one LiDAR observation."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.execute("""
            INSERT INTO lidar_observations (
                timestamp,
                robot_id,
                total_measurements,
                valid_measurements,
                nearest_distance
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            robot_id,
            total_measurements,
            valid_measurements,
            nearest_distance
        ))


def get_recent_observations(limit=10):
    """Retrieve the most recent LiDAR observations."""

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT *
            FROM lidar_observations
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [dict(row) for row in rows]


def get_robot_observations(robot_id, limit=10):
    """Retrieve observations belonging to a particular robot."""

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT *
            FROM lidar_observations
            WHERE robot_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (robot_id, limit)).fetchall()

    return [dict(row) for row in rows]


# --------------------------------------------------
# ROBOT STATUS MANAGEMENT
# --------------------------------------------------

def update_robot_status(robot_id, status, current_task_id=None):
    """Insert or update the operational status of a robot."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.execute("""
            INSERT INTO robot_status (
                robot_id,
                status,
                last_seen,
                current_task_id
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(robot_id)
            DO UPDATE SET
                status = excluded.status,
                last_seen = excluded.last_seen,
                current_task_id = excluded.current_task_id
        """, (
            robot_id,
            status,
            timestamp,
            current_task_id
        ))


def get_all_robot_status():
    """Retrieve the status of all registered robots."""

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT *
            FROM robot_status
            ORDER BY robot_id
        """).fetchall()

    return [dict(row) for row in rows]


# --------------------------------------------------
# MISSION MANAGEMENT
# --------------------------------------------------

def create_mission(mission_name):
    """Create a new search-and-rescue mission."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        cursor = connection.execute("""
            INSERT INTO missions (
                mission_name,
                start_time,
                status
            )
            VALUES (?, ?, ?)
        """, (
            mission_name,
            timestamp,
            'ACTIVE'
        ))

        return cursor.lastrowid


def update_mission_status(mission_id, status):
    """Update the status of a mission."""

    end_time = get_timestamp() if status == 'COMPLETED' else None

    with sqlite3.connect(DATABASE_PATH) as connection:

        if end_time:
            connection.execute("""
                UPDATE missions
                SET status = ?, end_time = ?
                WHERE mission_id = ?
            """, (status, end_time, mission_id))

        else:
            connection.execute("""
                UPDATE missions
                SET status = ?
                WHERE mission_id = ?
            """, (status, mission_id))


def get_all_missions():
    """Retrieve all missions."""

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT *
            FROM missions
            ORDER BY mission_id DESC
        """).fetchall()

    return [dict(row) for row in rows]


# --------------------------------------------------
# SEARCH TASK MANAGEMENT
# --------------------------------------------------

def create_search_task(
    mission_id,
    search_zone,
    robot_id=None,
    task_description=None
):
    """Create a search task under an existing mission."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        cursor = connection.execute("""
            INSERT INTO search_tasks (
                mission_id,
                robot_id,
                search_zone,
                task_description,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mission_id,
            robot_id,
            search_zone,
            task_description,
            'PENDING',
            timestamp,
            timestamp
        ))

        return cursor.lastrowid


def update_task_status(task_id, status):
    """Update the status of a search task."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.execute("""
            UPDATE search_tasks
            SET status = ?, updated_at = ?
            WHERE task_id = ?
        """, (
            status,
            timestamp,
            task_id
        ))


def get_all_search_tasks(mission_id=None):
    """Retrieve all tasks or tasks belonging to one mission."""

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.row_factory = sqlite3.Row

        if mission_id is not None:

            rows = connection.execute("""
                SELECT *
                FROM search_tasks
                WHERE mission_id = ?
                ORDER BY task_id
            """, (mission_id,)).fetchall()

        else:

            rows = connection.execute("""
                SELECT *
                FROM search_tasks
                ORDER BY task_id
            """).fetchall()

    return [dict(row) for row in rows]


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    initialize_database()

# --------------------------------------------------
# ROBOT POSITION MANAGEMENT
# --------------------------------------------------

def save_robot_position(robot_id, x, y, z=0.0):

    """Save a robot's position in the database."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.execute("""
            INSERT INTO robot_positions (
                robot_id, x, y, z, timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """, (robot_id, x, y, z, timestamp))


def get_latest_robot_positions():

    """Retrieve the latest recorded position of each robot."""

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT p.*
            FROM robot_positions p
            INNER JOIN (
                SELECT robot_id, MAX(id) AS latest_id
                FROM robot_positions
                GROUP BY robot_id
            ) latest
            ON p.id = latest.latest_id
        """).fetchall()

    return [dict(row) for row in rows]

def assign_task_to_robot(task_id, robot_id):
    """Assign a task to a robot and mark it IN_PROGRESS."""

    timestamp = get_timestamp()

    with sqlite3.connect(DATABASE_PATH) as connection:

        connection.execute("""
            UPDATE search_tasks
            SET robot_id = ?,
                status = ?,
                updated_at = ?
            WHERE task_id = ?
        """, (
            robot_id,
            "IN_PROGRESS",
            timestamp,
            task_id
        ))
