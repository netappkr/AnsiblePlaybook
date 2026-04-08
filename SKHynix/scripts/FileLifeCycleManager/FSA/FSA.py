#!/usr/bin/env python3

# -------------------------
# 외부 라이브러리 import
# -------------------------
import requests                 # ONTAP REST API 호출
import urllib3                 # HTTPS 경고 비활성화
import argparse                # CLI 인자 처리
import json                    # JSON 파싱
import logging                 # 로그 처리
import traceback               # 에러 traceback 출력
import yaml                    # YAML 파싱
import re
import os
import sys
import subprocess              # 외부 명령 실행 (finger2)
from collections import deque  # BFS 탐색용 큐
from requests.models import PreparedRequest
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from collections import deque
from urllib.parse import quote # URL 인코딩

# -------------------------
# argparse
# -------------------------
# CLI 실행 시 입력받는 옵션 정의
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", type=str)   # 입력 파일 (JSON/YAML)
parser.add_argument("--prevfile", type=str)   # 입력 파일 (JSON/YAML)
parser.add_argument("-r", "--request", type=str)           # 실행할 기능 (분기 처리용)
parser.add_argument("--config", type=str)                  # config YAML 경로
parser.add_argument("--debug", action="store_true", help="enable debug logging")
args = parser.parse_args()

# -------------------------
# logging 설정
# -------------------------
# 로그 파일 경로 생성 (~user/logs/fsa.log)
home_dir = os.path.expanduser("~")
log_dir = os.path.join(home_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

log_file_path = os.path.join(log_dir, "fsa.log")

# debug 옵션 또는 환경변수 기반 로그 레벨 설정
log_level = "DEBUG" if args.debug else os.getenv("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("fsa")
logger.setLevel(getattr(logging, log_level, logging.INFO))

formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(funcName)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 파일 로그
file_handler = logging.FileHandler(log_file_path, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 콘솔 로그
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# ----------------------------------------
# analytics_bytes_used: ">1G" 옵션 계산을 위한 파싱 함수
# --------------------------------------
def parse_size_filter(expr: str):
    """
    ">1G" → (operator, bytes)
    """
    match = re.match(r"(>=|<=|>|<|==)?\s*(\d+)([KMGTP]?)", expr.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid size filter: {expr}")

    op, value, unit = match.groups()

    value = int(value)
    unit = unit.upper()

    unit_map = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
        "P": 1024**5,
    }

    bytes_value = value * unit_map.get(unit, 1)

    return op or "==", bytes_value

# ----------------------------------------
# analytics_bytes_used: ">1G" 옵션 계산을 위한 조건검사 함수
# --------------------------------------
def check_condition(value, op, threshold):
    if op == ">":
        return value > threshold
    elif op == ">=":
        return value >= threshold
    elif op == "<":
        return value < threshold
    elif op == "<=":
        return value <= threshold
    elif op == "==":
        return value == threshold
    else:
        return False

# -------------------------
# JSON / YAML
# -------------------------
def read_json(file):
    with open(file) as f:
        data = json.load(f)
    return data

def read_yaml(path):
    """
    YAML 파일을 읽어서 dict 형태로 반환
    """
    with open(path) as f:
        return yaml.safe_load(f)

# -------------------------
# YAML 검증
# -------------------------
def check_yaml_integrity(file_path):
    """
    config YAML 구조 검증
    - division key 필수
    """
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
    """
    ONTAP volume 정보를 기반으로
    FSA 스캔 대상(scan_objects) 생성
    """

    logger.info("[START] get_scan_objects")

    scan_objects = []
    domain = config.get("domain")          # 현재 코드에서는 미사용 (확장 대비)
    division = config.get("division", [])  # division 설정

    for cluster in data:
        try:
            cluster_info = cluster["cluster"]

            # ONTAP volume 목록 순회
            for volume in cluster["msg"]["records"]:
                name = volume.get("volume")
                path = volume.get("junction_path")
                uuid = volume.get("instance_uuid")
                analytics = volume.get("analytics_state")

                # junction_path 없거나 analytics OFF인 경우 제외
                if not path or analytics != "on":
                    continue

                # division 기준으로 scan object 생성
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
# USER 디렉토리 찾기 + 사용량 수집
# -------------------------
def find_and_collect_usage(scan_objects,usage_latest_path):
    """
    BFS 방식으로 디렉토리 탐색
    1. target 디렉토리(USER 등) 찾기
    2. 해당 하위 디렉토리 usage 수집
    """
    # -----------------------
    # 이전 데이터 로딩
    # -----------------------
    logger.info(f"[START] find_and_collect_usage count={len(scan_objects)}")

    prev_map = {}

    try:
        if usage_latest_path and os.path.exists(usage_latest_path):
            prev_data = read_yaml(usage_latest_path)

            if not prev_data:
                logger.warning(f"[WARN] empty previous file: {usage_latest_path}")
                prev_data = []

            for d in prev_data:
                try:
                    key = d.get("full_path")
                    used = d.get("bytes_used", 0)

                    if not key:
                        logger.error(f"[ERROR] {key}key does not exsit")
                        continue
                        
                    if not isinstance(used, (int, float)):
                        used = 0

                    prev_map[key] = used

                except Exception as e:
                    logger.warning(f"[WARN] invalid record skipped: {str(e)}")

        else:
            logger.info(f"[FIRST RUN] no previous file")

    except Exception as e:
        logger.error(f"[ERROR] failed to load previous data: {str(e)}")

    

    session = requests.Session()
    session.verify = False  # SSL 인증서 검증 비활성화

    results = []
    seen_paths = set()  # 중복 path 방지

    for obj in scan_objects:
        cluster = obj["cluster"]

        # ONTAP REST API URL 구성
        base_url = f"https://{cluster['ip']}/api/storage/volumes/{obj['vol_uuid']}/files"
        auth = (cluster["ID"], cluster["PW"])

        # 탐색 대상 디렉토리 목록
        targets = [p.get("dir") for p in obj["fsa_option"].get("path", [])]

        logger.info(f"[SEARCH] volume={obj['volume']} targets={targets}")

        # BFS 초기값 (루트부터 시작)
        queue = deque([("/", 1)])
        visited = set()
        found_roots = set()
        # config에서 필터 읽기
        filter_expr = obj["fsa_option"].get("analytics_bytes_used")

        if filter_expr:
            op, threshold = parse_size_filter(filter_expr)

        while queue:
            path, depth = queue.popleft()

            # depth 제한 및 방문 여부 체크
            if depth > 7 or path in visited:
                continue

            visited.add(path)

            try:
                encoded_path = quote(path if path else "/", safe="")
                url = f"{base_url}/{encoded_path}"

                logger.debug(f"[REQUEST] {url}")

                # 디렉토리 목록 조회
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
                logger.debug(f"[API] RES_RECODE={records}")

                for r in records:
                    name = r.get("name")
                    parent = r.get("path") or "/"
                    r_type = r.get("type")

                    # 불필요 디렉토리 제외
                    if name in [".", "..", ".snapshot"]:
                        continue

                    if r_type != "directory":
                        continue

                    # full path 생성
                    full_path = f"{parent.rstrip('/')}/{name}"

                    logger.debug(f"[PATH] {full_path}")

                    # target 디렉토리 발견
                    if name in targets:

                        if full_path in found_roots:
                            continue

                        logger.info(f"[FOUND ROOT] {full_path}")
                        found_roots.add(full_path)

                        # 하위 디렉토리 usage 조회
                        encoded_sub = quote(full_path, safe="")
                        sub_url = f"{base_url}/{encoded_sub}"

                        # 기본 params
                        params = {
                            "fields": "name,path,owner_id,analytics.bytes_used,type"
                        }

                        # config fsa_option 병합
                        # fsa_option에서 path 제외하고 params 반영
                        if "fsa_option" in obj:
                            for k, v in obj["fsa_option"].items():
                                if k == "path":
                                    continue
                                if k == "analytics_bytes_used":
                                    continue
                                params[k] = v

                        logger.debug(f"[REQUEST] {sub_url}")
                        logger.debug(f"[REQUEST_PARAMS] {params}")
                        res2 = session.get(
                            url=sub_url,
                            auth=auth,
                            params=params,
                            timeout=30
                        )

                        res2.raise_for_status()
                        sub_records = res2.json().get("records", [])

                        logger.debug(f"[USAGE API] path={full_path} count={len(sub_records)}")
                        logger.debug(f"[USAGE API] RES_RECODE={sub_records}")

                        for sr in sub_records:
                            sub_name = sr.get("name")
                            sub_parent = sr.get("path") or full_path
                            sub_type = sr.get("type")

                            if sub_name in [".", "..", ".snapshot"]:
                                continue

                            if sub_type != "directory":
                                continue

                            sub_full_path = f"{sub_parent.rstrip('/')}/{sub_name}"

                            seen_paths.add(sub_full_path)

                            owner = sr.get("owner_id")
                            used = sr.get("analytics", {}).get("bytes_used", 0)
                            # -----------------------
                            # diff 계산
                            # -----------------------
                            key = sub_full_path
                            prev_used = prev_map.get(key, 0)
                            diff = used - prev_used

                            # analytics_bytes_used: ">1G" 옵션 필터링
                            if filter_expr:
                                if not check_condition(used, op, threshold):
                                    continue

                            # owner_id → 사용자 정보 조회
                            username, email = get_user_info(owner)

                            # 결과 저장
                            results.append({
                                "division": obj["div"],
                                "volume": obj["volume"],
                                "user_dir": sub_name,
                                "full_path": sub_full_path,
                                "owner_id": owner,
                                "user_name": username,
                                "email": email,
                                "bytes_used": used,
                                "diff_bytes": diff
                            })

                        continue

                    # BFS 확장 (하위 디렉토리 탐색)
                    queue.append((full_path, depth + 1))

            except Exception as e:
                logger.error(f"[ERROR] path={path} {str(e)}")

    logger.info(f"[END] find_and_collect_usage result_count={len(results)}")
    return results

# -------------------------
# 사용자 정보 조회
# -------------------------
def get_user_info(owner_id):
    """
    owner_id → 사용자 이름 / 이메일 변환
    (finger2 명령어 활용)
    """
    try:
        res = subprocess.run(
            ["finger2", str(owner_id)],
            capture_output=True,
            text=True
        )

        name = "unknown"
        email = "unknown"

        for line in res.stdout.splitlines():
            if "Name" in line:
                name = line.split(":")[1].strip()
            if "E-mail" in line:
                email = line.split(":")[1].strip()

        return name, email

    except Exception:
        return "unknown", "unknown"

# -------------------------
# 사용자별 그룹핑
# -------------------------
def group_by_user(data):
    """
    email 기준으로 데이터 그룹핑
    (메일 발송 단위)
    """
    grouped = {}

    for d in data:
        email = d.get("email", "unknown")

        if email not in grouped:
            grouped[email] = []

        grouped[email].append(d)

    return grouped

# -------------------------
# 사용자 HTML 생성
# -------------------------
def build_html_per_user(data):
    """
    개인 메일용 HTML 생성
    (Volume / Directory / Usage만 표시)
    """

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
# HTML 생성
# -------------------------
def build_mail(data):
    import collections

    volume_map = collections.defaultdict(list)

    # -----------------------
    # 1. volume 그룹핑
    # -----------------------
    for d in data:
        volume_map[d.get("volume")].append(d)

    results = []

    # -----------------------
    # 2. volume별 메일 생성
    # -----------------------
    for volume, items in volume_map.items():

        email_set = set()

        for d in items:
            email = d.get("email")
            if email and email != "unknown":
                email_set.add(email)

        # -----------------------
        # HTML 생성
        # -----------------------
        html = f"""
<html>
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: Arial; background-color:#0b1220; color:white; }}
    table {{ border-collapse: collapse; margin-top: 20px; width:100%; }}
    th, td {{ border: 1px solid #444; padding: 8px; text-align: center; }}
    th {{ background-color: #1f2a44; }}
</style>
</head>
<body>

<h2>Volume: {volume}</h2>

<table>
"""

        # path row
        html += "<tr>"
        for d in items:
            html += f"<th colspan='4'>{d.get('full_path')}</th>"
        html += "</tr>"

        # header row
        html += "<tr>"
        for _ in items:
            html += """
            <th>total (GB)</th>
            <th>diff (GB)</th>
            <th>user</th>
            <th>name</th>
            """
        html += "</tr>"

        # data row
        html += "<tr>"

        for d in items:
            total_gb = d.get("bytes_used", 0) / (1024**3)
            diff_gb = d.get("diff_bytes", 0) / (1024**3)

            if diff_gb > 0:
                color = "red"
                sign = "+"
            elif diff_gb < 0:
                color = "deepskyblue"
                sign = ""
            else:
                color = "white"
                sign = ""

            html += f"""
            <td>{total_gb:.2f}</td>
            <td style='color:{color}'>{sign}{diff_gb:.2f}</td>
            <td>{d.get("owner_id")}</td>
            <td>{d.get("user_dir")}</td>
            """

        html += "</tr>"
        html += "</table></body></html>"

        results.append({
            "volume": volume,
            "emails": list(email_set),
            "html": html
        })

    return results

# -------------------------
# main
# -------------------------
def main():
    """
    request 값에 따라 기능 분기
    """

    try:
        # scan object 생성
        if args.request == "get_scan_object":
            data = read_json(args.file)
            config = check_yaml_integrity(args.config)
            result = get_scan_objects(data, config)
            print(yaml.safe_dump(result, sort_keys=False))

        # usage 수집
        elif args.request == "find_and_collect_usage":
            data = read_yaml(args.file)
            result = find_and_collect_usage(data,args.prevfile)
            print(yaml.safe_dump(result, sort_keys=False))

        # 메일 생성
        elif args.request == "build_mail":
            data = read_yaml(args.file)

            result = build_mail(data)

            print(yaml.safe_dump(result, sort_keys=False))
        else:
            logger.error(f"invalid request: {args.request}")
            print("invalid request")

    except Exception:
        logger.error(traceback.format_exc())
        print(traceback.format_exc(), file=sys.stderr)

if __name__ == "__main__":
    main()