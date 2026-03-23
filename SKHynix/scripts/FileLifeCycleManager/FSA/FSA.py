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

def find_directories(scan_objects):

    logger.info(f"[START] find_directories count={len(scan_objects)}")

    session = requests.Session()
    session.verify = False

    results = []
    seen_paths = set()  # 🔥 중복 방지

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
                logger.debug(f"[AUTH] user={auth[0]} password=****")
                logger.debug(f"[ENCODED] raw={path} encoded={encoded_path}")

                res = session.get(
                    url,
                    auth=auth,
                    params={
                        "type": "directory",
                        "fields": "name,path"
                    },
                    timeout=30
                )

                logger.debug(f"[RESPONSE] status={res.status_code}")
                logger.debug(f"[RESPONSE_BODY] {res.text[:300]}")

                res.raise_for_status()
                records = res.json().get("records", [])

                logger.debug(f"[API] path={path} count={len(records)}")

                for r in records:
                    name = r.get("name")
                    parent = r.get("path") or "/"

                    if name in [".", "..", ".snapshot"]:
                        continue

                    # 🔥 핵심: full_path 생성
                    full_path = f"{parent.rstrip('/')}/{name}"

                    logger.debug(f"[PATH] parent={parent} name={name} full={full_path}")

                    # 🔥 target 발견
                    if name in targets:

                        if full_path in found_roots:
                            continue

                        logger.info(f"[FOUND ROOT] {full_path}")
                        found_roots.add(full_path)

                        # 🔥 하위 1-depth 조회
                        encoded = quote(full_path, safe="")
                        sub_url = f"{base_url}/{encoded}"

                        logger.debug(f"[REQUEST] {sub_url}")

                        res2 = session.get(
                            sub_url,
                            auth=auth,
                            params={
                                "type": "directory",
                                "fields": "name,path"
                            },
                            timeout=10
                        )

                        logger.debug(f"[RESPONSE] status={res2.status_code}")
                        logger.debug(f"[RESPONSE_BODY] {res2.text[:300]}")

                        res2.raise_for_status()
                        sub_records = res2.json().get("records", [])

                        logger.debug(f"[API] sub_path={full_path} count={len(sub_records)}")

                        for sr in sub_records:
                            sub_name = sr.get("name")
                            sub_parent = sr.get("path") or full_path

                            if sub_name in [".", "..", ".snapshot"]:
                                continue

                            # 🔥 핵심: sub full path 생성
                            sub_path = f"{sub_parent.rstrip('/')}/{sub_name}"

                            if sub_path not in seen_paths:
                                seen_paths.add(sub_path)

                                results.append({
                                    "cluster": cluster,
                                    "volume": obj["volume"],
                                    "division": obj["div"],
                                    "found_path": sub_path,
                                    "vol_uuid": obj["vol_uuid"]
                                })

                        # 🔥 target 밑은 더 안탐
                        continue

                    # 🔥 이미 root 잡힌 경로 하위 skip
                    if any(path.startswith(root) for root in found_roots):
                        continue

                    # 🔥 BFS 확장 (핵심)
                    queue.append((full_path, depth + 1))

            except Exception as e:
                logger.error(f"[ERROR] find_dir path={path} {str(e)}")

    logger.info(f"[END] find_directories found={len(results)}")
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

        name = "unknown"
        email = "unknown"

        for line in res.stdout.splitlines():

            if "Name:" in line:
                name = line.split("Name:")[1].strip()

            if "E-mail" in line:
                email = line.split(":")[1].strip()

        return name, email

    except Exception as e:
        logger.error(f"[ERROR] get_user_info owner={owner_id} {str(e)}")
        return "unknown", "unknown"

# -------------------------
# usage 조회
# -------------------------

def get_usage(found_dirs):

    logger.info(f"[START] get_usage count={len(found_dirs)}")

    session = requests.Session()
    session.verify = False

    result = []

    for item in found_dirs:
        cluster = item["cluster"]

        try:
            base_url = f"https://{cluster['ip']}/api/storage/volumes/{item['vol_uuid']}/files"

            # 🔥 path 기반 방식으로 변경
            path = item["found_path"] if item["found_path"] else "/"
            encoded_path = quote(path, safe="")

            url = f"{base_url}/{encoded_path}"

            logger.debug(f"[REQUEST] {url}")
            logger.debug(f"[AUTH] user={cluster['ID']} password=****")
            logger.debug(f"[ENCODED] raw={path} encoded={encoded_path}")
            res = session.get(
                url,
                auth=(cluster["ID"], cluster["PW"]),
                params={
                    "type": "directory",
                    "fields": "name,path,owner_id,analytics.bytes_used"
                },
                timeout=10
            )

            logger.debug(f"[RESPONSE] status={res.status_code}")
            logger.debug(f"[RESPONSE_BODY] {res.text[:300]}")

            res.raise_for_status()
            records = res.json().get("records", [])

            logger.info(f"[QUERY] path={path} count={len(records)}")

            for r in records:
                if r.get("name") in [".", ".."]:
                    continue

                dir_name = r.get("name")
                parent = r.get("path") or "/"
                full_path = f"{parent.rstrip('/')}/{dir_name}"

                owner = r.get("owner_id")
                used = r.get("analytics", {}).get("bytes_used", 0)
                username, email = get_user_info(owner)
                result.append({
                    "division": item["division"],
                    "volume": item["volume"],
                    "dir_name": dir_name,
                    "full_path": full_path,
                    "owner_id": owner,
                    "user": username,
                    "email": email,
                    "bytes_used": used
                })

        except Exception as e:
            logger.error(f"[ERROR] usage path={item['found_path']} {str(e)}")

    result.sort(key=lambda x: x["bytes_used"], reverse=True)

    logger.info(f"[END] get_usage users={len(result)}")
    return result

# -------------------------
# HTML
# -------------------------
def build_html(data):

    html = """
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        h2 {
            margin-bottom: 10px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
        }
        th {
            background-color: #f2f2f2;
            padding: 8px;
            border: 1px solid #ddd;
        }
        td {
            padding: 8px;
            border: 1px solid #ddd;
            text-align: center;
        }
        tr:nth-child(even) {
            background-color: #fafafa;
        }
    </style>
</head>
<body>

<h2>Directory Usage Report</h2>

<table>
    <tr>
        <th>Division</th>
        <th>Volume</th>
        <th>User</th>
        <th>Usage (GB)</th>
        <th>Email</th>
    </tr>
"""

    for d in data:
        gb = d["bytes_used"] / (1024**3)

        html += f"""
    <tr>
        <td>{d['division']}</td>
        <td>{d['volume']}</td>
        <td>{d['full_path']}</td>
        <td>{gb:.2f}</td>
        <td>{d['user']}</td>
        <td>{d['email']}</td>
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

        elif args.request == "find_dir":
            data = read_yaml(args.file[0])
            print(yaml.safe_dump(find_directories(data), sort_keys=False))

        elif args.request == "get_usage":
            data = read_yaml(args.file[0])
            print(yaml.safe_dump(get_usage(data), sort_keys=False))

        elif args.request == "build_mail":
            data = read_yaml(args.file[0])
            print(build_html(data))

        else:
            logger.error(f"invalid request: {args.request}")
            print("invalid request")

    except Exception:
        logger.error(traceback.format_exc())
        print(traceback.format_exc(), file=sys.stderr)

if __name__ == "__main__":
    main()