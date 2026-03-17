#!/usr/bin/env python3

import argparse
import yaml
import sys
import os

DEFAULT_DB_PATH = "/etc/finger2/user_db.yaml"

def load_users(file_path):
    with open(file_path) as f:
        return yaml.safe_load(f)["users"]

def print_user(user_id, user):
    print(f"""Login name : {user_id}
Employee ID : {user['empid']}
Name : {user['name']}
Dept. : {user['dept']}
Job position : {user['position']}
Workstate : {user['workstate']}
E-mail : {user['email']}
Home : {user['home']}
Shell : {user['shell']}
""")

def print_user_list(users):
    print("Available Users:\n")
    for user_id, user in users.items():
        print(f"{user_id}  {user['name']}  ({user['email']})")

def main():
    parser = argparse.ArgumentParser(
        description="User lookup tool (finger2 replacement)"
    )

    parser.add_argument(
        "user_id",
        help="User ID (owner_id) to lookup OR 'list'"
    )

    parser.add_argument(
        "-f", "--file",
        help="YAML user database file (default: /etc/finger2/user_db.yaml)"
    )

    args = parser.parse_args()

    yaml_path = args.file if args.file else DEFAULT_DB_PATH

    if not os.path.exists(yaml_path):
        print(f"YAML file not found: {yaml_path}")
        sys.exit(1)

    users = load_users(yaml_path)

    # 🔥 list 기능 추가
    if args.user_id.lower() == "list":
        print_user_list(users)
        return

    user = users.get(args.user_id)

    if not user:
        print("User not found")
        sys.exit(1)

    print_user(args.user_id, user)

if __name__ == "__main__":
    main()