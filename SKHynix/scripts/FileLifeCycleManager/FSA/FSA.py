#!/usr/bin/env python3

import requests
import urllib3
import argparse
import json
import logging
import traceback
import yaml
import re
import os
import sys
import subprocess
from collections import deque
from requests.models import PreparedRequest
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from collections import deque
from urllib.parse import quote

# -------------------------
# argparse
# -------------------------
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", type=str, nargs='+')
parser.add_argument("-r", "--request", type=str)
parser.add_argument("--config", type=str)
parser.add_argument("--debug", action="store_true", help="enable debug logging")
args = parser.parse_args()

# -------------------------
# logging 설정
# -------------------------
home_dir = os.path.expanduser("~")
log_dir = os.path.join(home_dir, "logs")

os.makedirs(log_dir, exist_ok=True)

log_file_path = os.path.join(log_dir, "fsa.log")

log_level = "DEBUG" if args.debug else os.getenv("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("fsa")
logger.setLevel(getattr(logging, log_level, logging.INFO))

formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(funcName)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_handler = logging.FileHandler(log_file_path, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# -------------------------
# JSON / YAML
# -------------------------
def read_json(filelist):
    data = {}
    for f in filelist:
        with open(f) as file:
            data[f] = json.load(file)
    return data

def read_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

# -------------------------
# YAML 검증
# -------------------------
def check_yaml_integrity(file_path):
    try:
        with open(file_path) as file:
            config = yaml.safe_load(file)

        if "division" not in config:
            raise ValueError("division key missing")

        return config

    except Exception as e:
        logger.error(f"[ERROR] YAML validation: {str(e)}")
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)

# -------------------------
# scan object 생성
# -------------------------
def get_scan_objects(data, config):

    logger.info("[START] get_scan_objects")

    scan_objects = []
    domain = config.get("domain")
    division = config.get("division", [])

    for cluster in data:
        try:
            cluster_info = cluster["cluster"]

            for volume in cluster["msg"]["records"]:
                name = volume.get("volume")
                path = volume.get("junction_path")
                uuid = volume.get("instance_uuid")
                analytics = volume.get("analytics_state")

                if not path or analytics != "on":
                    continue

                for div in division:
                    if "fsa_option" not in div:
                        continue

                    scan_objects.append({
                        "cluster": cluster_info,
                        "volume": name,
                        "vol_uuid": uuid,
                        "div": div["name"],
                        "fsa_option": div["fsa_option"]
                    })

                    logger.debug(f"[ADD] volume={name}")

        except Exception:
            logger.error(traceback.format_exc())

    logger.info(f"[END] get_scan_objects count={len(scan_objects)}")
    return scan_objects

# -------------------------
# USER 디렉토리 찾기
# -------------------------

def find_and_collect_usage(scan_objects):

    logger.info(f"[START] find_and_collect_usage count={len(scan_objects)}")

    session = requests.Session()
    session.verify = False

    results = []
    seen_paths = set()  # 중복 방지

    for obj in scan_objects:
        cluster = obj["cluster"]
        base_url = f"https://{cluster['ip']}/api/storage/volumes/{obj['vol_uuid']}/files"
        auth = (cluster["ID"], cluster["PW"])

        targets = [p.get("dir") for p in obj["fsa_option"].get("path", [])]

        logger.info(f"[SEARCH] volume={obj['volume']} targets={targets}")

        queue = deque([("/", 1)])
        visited = set()
        found_roots = set()

        while queue:
            path, depth = queue.popleft()

            if depth > 7 or path in visited:
                continue

            visited.add(path)

            try:
                encoded_path = quote(path if path else "/", safe="")
                url = f"{base_url}/{encoded_path}"

                logger.debug(f"[REQUEST] {url}")

                res = session.get(
                    url,
                    auth=auth,
                    params={
                        "type": "directory",
                        "fields": "name,path,type"
                    },
                    timeout=30
                )

                res.raise_for_status()
                records = res.json().get("records", [])

                logger.debug(f"[API] path={path} count={len(records)}")

                for r in records:
                    name = r.get("name")
                    parent = r.get("path") or "/"
                    r_type = r.get("type")

                    if name in [".", "..", ".snapshot"]:
                        continue

                    if r_type != "directory":
                        continue

                    # 🔥 full path 생성
                    full_path = f"{parent.rstrip('/')}/{name}"

                    logger.debug(f"[PATH] {full_path}")

                    # 🔥 target 발견
                    if name in targets:

                        if full_path in found_roots:
                            continue

                        logger.info(f"[FOUND ROOT] {full_path}")
                        found_roots.add(full_path)

                        # 🔥 하위 디렉토리 조회 + usage 수집
                        encoded_sub = quote(full_path, safe="")
                        sub_url = f"{base_url}/{encoded_sub}"

                        res2 = session.get(
                            sub_url,
                            auth=auth,
                            params={
                                "type": "directory",
                                "fields": "name,path,owner_id,analytics.bytes_used,type"
                            },
                            timeout=10
                        )

                        res2.raise_for_status()
                        sub_records = res2.json().get("records", [])

                        logger.debug(f"[USAGE API] path={full_path} count={len(sub_records)}")

                        for sr in sub_records:
                            sub_name = sr.get("name")
                            sub_parent = sr.get("path") or full_path
                            sub_type = sr.get("type")

                            if sub_name in [".", "..", ".snapshot"]:
                                continue

                            if sub_type != "directory":
                                continue

                            sub_full_path = f"{sub_parent.rstrip('/')}/{sub_name}"

                            if sub_full_path in seen_paths:
                                continue

                            seen_paths.add(sub_full_path)

                            owner = sr.get("owner_id")
                            used = sr.get("analytics", {}).get("bytes_used", 0)

                            username, email = get_user_info(owner)

                            results.append({
                                "division": obj["div"],
                                "volume": obj["volume"],
                                "user_dir": sub_name,
                                "full_path": sub_full_path,
                                "owner_id": owner,
                                "user_name": username,
                                "email": email,
                                "bytes_used": used
                            })

                        continue

                    # 🔥 이미 target 하위면 탐색 skip
                    if any(path.startswith(root) for root in found_roots):
                        continue

                    # 🔥 BFS 확장
                    queue.append((full_path, depth + 1))

            except Exception as e:
                logger.error(f"[ERROR] path={path} {str(e)}")

    logger.info(f"[END] find_and_collect_usage result_count={len(results)}")
    return results

# -------------------------
# username email 조회
# -------------------------
def get_user_info(owner_id):
    try:
        res = subprocess.run(
            ["finger2", str(owner_id)],
            capture_output=True,
            text=True
        )
        logger.debug(f"[debug] res={res}")
        name = "unknown"
        email = "unknown"

        for line in res.stdout.splitlines():

            if "Name" in line:
                name = line.split(":")[1].strip()

            if "E-mail" in line:
                email = line.split(":")[1].strip()
        logger.debug(f"[debug] owner_id={owner_id}, name={name}, email={email}")
        return name, email

    except Exception as e:
        logger.error(f"[ERROR] get_user_info owner={owner_id} {str(e)}")
        return "unknown", "unknown"

def group_by_user(data):
    grouped = {}

    for d in data:
        email = d.get("email", "unknown")

        if email not in grouped:
            grouped[email] = []

        grouped[email].append(d)

    return grouped

def build_html_per_user(data):

    html = """
<html>
<body>
<h2>My Directory Usage</h2>
<table border="1">
<tr>
    <th>Volume</th>
    <th>Directory</th>
    <th>Usage (GB)</th>
</tr>
"""

    for d in data:
        gb = d.get("bytes_used", 0) / (1024**3)

        html += f"""
<tr>
    <td>{d.get('volume')}</td>
    <td>{d.get('full_path')}</td>
    <td>{gb:.2f}</td>
</tr>
"""

    html += "</table></body></html>"

    return html

# -------------------------
# HTML
# -------------------------
def build_html(data):

    html = """
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>

<h2>Directory Usage Report</h2>

<table>
<tr>
    <th>Division</th>
    <th>Volume</th>
    <th>User Dir</th>
    <th>User Name</th>
    <th>Email</th>
    <th>Usage (GB)</th>
</tr>
"""

    for d in data:
        gb = d.get("bytes_used", 0) / (1024**3)

        html += f"""
<tr>
    <td>{d.get('division')}</td>
    <td>{d.get('volume')}</td>
    <td>{d.get('user_dir')}</td>
    <td>{d.get('user_name')}</td>
    <td>{d.get('email')}</td>
    <td>{gb:.2f}</td>
</tr>
"""

    html += """
</table>
</body>
</html>
"""

    return html
# -------------------------
# main
# -------------------------
def main():
    try:
        if args.request == "get_scan_object":
            data = read_json(args.file)
            config = check_yaml_integrity(args.config)
            result = get_scan_objects(data[args.file[0]], config)
            print(yaml.safe_dump(result, sort_keys=False))

        elif args.request == "find_and_collect_usage":
            data = read_yaml(args.file[0])
            result = find_and_collect_usage(data)
            print(yaml.safe_dump(result, sort_keys=False))

        elif args.request == "build_mail_per_user":
            data = read_yaml(args.file[0])

            grouped = group_by_user(data)

            result = []

            for email, items in grouped.items():
                html = build_html_per_user(items)

                result.append({
                    "email": email,
                    "html": html
                })

            print(yaml.safe_dump(result, sort_keys=False))

        else:
            logger.error(f"invalid request: {args.request}")
            print("invalid request")

    except Exception:
        logger.error(traceback.format_exc())
        print(traceback.format_exc(), file=sys.stderr)

if __name__ == "__main__":
    main()