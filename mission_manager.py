
"""
Edge Cloud - Mission Manager

Handles the lifecycle of disaster search missions:
1. Create missions
2. Pause missions
3. Resume missions
4. Complete missions
5. View mission details
6. List all missions
"""

import sys
import os

# Allow importing database.py from the same src directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database


# --------------------------------------------------
# MISSION CREATION
# --------------------------------------------------

def create_new_mission(mission_name):
    """Create a new disaster search mission."""

    if not mission_name or not mission_name.strip():
        print("Error: Mission name cannot be empty.")
        return None

    mission_id = database.create_mission(mission_name.strip())

    print(f"Mission created successfully!")
    print(f"Mission ID: {mission_id}")
    print(f"Mission Name: {mission_name}")
    print("Status: ACTIVE")

    return mission_id


# --------------------------------------------------
# MISSION STATUS MANAGEMENT
# --------------------------------------------------

def pause_mission(mission_id):
    """Pause an active mission."""

    missions = database.get_all_missions()

    mission = next(
        (m for m in missions if m["mission_id"] == mission_id),
        None
    )

    if mission is None:
        print("Error: Mission not found.")
        return False

    if mission["status"] != "ACTIVE":
        print("Error: Only ACTIVE missions can be paused.")
        return False

    database.update_mission_status(mission_id, "PAUSED")

    print(f"Mission {mission_id} paused successfully.")
    return True


def resume_mission(mission_id):
    """Resume a paused mission."""

    missions = database.get_all_missions()

    mission = next(
        (m for m in missions if m["mission_id"] == mission_id),
        None
    )

    if mission is None:
        print("Error: Mission not found.")
        return False

    if mission["status"] != "PAUSED":
        print("Error: Only PAUSED missions can be resumed.")
        return False

    database.update_mission_status(mission_id, "ACTIVE")

    print(f"Mission {mission_id} resumed successfully.")
    return True


def complete_mission(mission_id):
    """Mark a mission as completed."""

    missions = database.get_all_missions()

    mission = next(
        (m for m in missions if m["mission_id"] == mission_id),
        None
    )

    if mission is None:
        print("Error: Mission not found.")
        return False

    if mission["status"] not in ("ACTIVE", "PAUSED"):
        print("Error: Mission cannot be completed in its current state.")
        return False

    database.update_mission_status(mission_id, "COMPLETED")

    print(f"Mission {mission_id} completed successfully.")
    return True


# --------------------------------------------------
# MISSION MONITORING
# --------------------------------------------------

def get_mission_details(mission_id):
    """Retrieve mission information and its associated tasks."""

    missions = database.get_all_missions()

    mission = next(
        (m for m in missions if m["mission_id"] == mission_id),
        None
    )

    if mission is None:
        print("Error: Mission not found.")
        return None

    tasks = database.get_all_search_tasks(mission_id)

    details = {
        "mission": mission,
        "tasks": tasks
    }

    print("\n========== MISSION DETAILS ==========")
    print(f"Mission ID: {mission['mission_id']}")
    print(f"Mission Name: {mission['mission_name']}")
    print(f"Status: {mission['status']}")
    print(f"Start Time: {mission['start_time']}")
    print(f"End Time: {mission['end_time']}")

    print("\nAssociated Search Tasks:")

    if not tasks:
        print("No search tasks available.")

    for task in tasks:
        print(
            f"Task {task['task_id']} | "
            f"Zone: {task['search_zone']} | "
            f"Robot: {task['robot_id']} | "
            f"Status: {task['status']}"
        )

    print("=====================================\n")

    return details


def list_all_missions():
    """Display all missions stored in the database."""

    missions = database.get_all_missions()

    print("\n========== ALL MISSIONS ==========")

    if not missions:
        print("No missions found.")
        return []

    for mission in missions:
        print(
            f"ID: {mission['mission_id']} | "
            f"Name: {mission['mission_name']} | "
            f"Status: {mission['status']}"
        )

    print("==================================\n")

    return missions


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    print("\nEDGE CLOUD - MISSION MANAGER")

    database.initialize_database()

    list_all_missions()