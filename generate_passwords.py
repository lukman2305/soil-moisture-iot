#!/usr/bin/env python3
"""
generate_passwords.py
---------------------
Interactive tool to add/update users in auth_config.yaml with hashed passwords.

Usage:
    python generate_passwords.py

Run this whenever you need to:
  - Add a new user
  - Change someone's password
  - Set up auth_config.yaml for the first time
"""

import sys
from pathlib import Path

try:
    import bcrypt
    import yaml
except ImportError:
    print("Missing packages. Run: pip install bcrypt PyYAML")
    sys.exit(1)


AUTH_CONFIG_PATH = Path(__file__).resolve().parent / "auth_config.yaml"

# ── Default template used when auth_config.yaml does not exist yet ─────────
DEFAULT_CONFIG = {
    "credentials": {"usernames": {}},
    "cookie": {
        "expiry_days": 7,
        "key": "soil_monitor_secret_key_change_me",
        "name": "soil_monitor_auth",
    },
}


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def load_config() -> dict:
    if AUTH_CONFIG_PATH.exists():
        with open(AUTH_CONFIG_PATH) as f:
            return yaml.safe_load(f) or DEFAULT_CONFIG
    return DEFAULT_CONFIG


def save_config(config: dict) -> None:
    with open(AUTH_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    print(f"\n✅ Saved to {AUTH_CONFIG_PATH}")


def list_users(config: dict) -> None:
    users = config.get("credentials", {}).get("usernames", {})
    if not users:
        print("  (no users yet)")
        return
    for username, info in users.items():
        print(f"  • {username}  ({info.get('name', '?')})  —  {info.get('email', '')}")


def add_or_update_user(config: dict) -> None:
    print("\n── Add / Update User ──────────────────────────────")
    username = input("Username (no spaces): ").strip().lower()
    if not username:
        print("Cancelled.")
        return

    users = config.setdefault("credentials", {}).setdefault("usernames", {})
    existing = users.get(username, {})

    name = input(f"Display name [{existing.get('name', '')}]: ").strip() or existing.get("name", username)
    email = input(f"Email [{existing.get('email', '')}]: ").strip() or existing.get("email", "")

    while True:
        password = input("New password (leave blank to keep existing): ").strip()
        if not password and existing.get("password"):
            hashed = existing["password"]
            print("  Password unchanged.")
            break
        if len(password) < 6:
            print("  Password must be at least 6 characters.")
            continue
        confirm = input("Confirm password: ").strip()
        if password != confirm:
            print("  Passwords do not match. Try again.")
            continue
        hashed = hash_password(password)
        print("  Password hashed ✓")
        break

    users[username] = {"email": email, "name": name, "password": hashed}
    save_config(config)
    print(f"  User '{username}' saved.")


def remove_user(config: dict) -> None:
    print("\n── Remove User ─────────────────────────────────────")
    users = config.get("credentials", {}).get("usernames", {})
    if not users:
        print("  No users to remove.")
        return
    username = input("Username to remove: ").strip().lower()
    if username not in users:
        print(f"  '{username}' not found.")
        return
    confirm = input(f"Delete user '{username}'? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("  Cancelled.")
        return
    del users[username]
    save_config(config)
    print(f"  User '{username}' removed.")


def main() -> None:
    print("═══════════════════════════════════════════════════")
    print("   Soil Monitor — User Manager")
    print("═══════════════════════════════════════════════════")

    config = load_config()

    while True:
        print("\nCurrent users:")
        list_users(config)
        print("\nOptions:")
        print("  1  Add / update a user")
        print("  2  Remove a user")
        print("  3  Quit")
        choice = input("Choice: ").strip()

        if choice == "1":
            add_or_update_user(config)
        elif choice == "2":
            remove_user(config)
        elif choice == "3":
            break
        else:
            print("Invalid choice.")

    print("\nDone. Restart Streamlit for changes to take effect.")


if __name__ == "__main__":
    main()
