#!/usr/bin/env python3

# -------------------------
# 외부 라이브러리 import
# -------------------------
import requests                 # REST API 호출용
import urllib3                 # HTTPS 경고 제거용
import argparse                # CLI 인자 처리
import json                    # JSON 처리
import logging                 # 로깅
import traceback               # 에러 traceback 출력
import yaml                    # YAML 처리
import os
import sys
import subprocess              # 외부 명령 실행 (finger2)
from collections import deque  # BFS 탐색용 큐
from urllib.parse import quote # URL 인코딩

# HTTPS 인증 경고 제거
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -------------------------
# argparse 설정
# -------------------------
# CLI 실행 시 사용할 옵션 정의
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", type=str, nargs='+')   # 입력 파일
parser.add_argument("-r", "--request", type=str)           # 수행할 기능
parser.add_argument("--config", type=str)                  # config 파일
parser.add_argument("--debug", action="store_true")        # debug 모드
args = parser.parse_args()

# -------------------------
# logging 설정
# -------------------------
# 로그 파일 위치 및 포맷 정의
home_dir = os.path.expanduser("~")
log_dir = os.path.join(home_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

log_file_path = os.path.join(log_dir, "fsa.log")

# debug 옵션 또는 환경변수 기반 로그 레벨 설정
log_level = "DEBUG" if args.debug else os.getenv("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("fsa")
logger.setLevel(getattr(logging, log_level, logging.INFO))

formatter = logging.Formatter(
    '%(asctime)s %(levelname)s [%(funcName)s] %(message)s'
)

# 파일 로그
file_handler = logging.FileHandler(log_file_path, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 콘솔 로그
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# -------------------------
# JSON / YAML 읽기 함수
# -------------------------
def read_json(filelist):
    """여러 JSON 파일을 읽어서 dict 형태로 반환"""
    data = {}
    for f in filelist:
        with open(f) as file:
            data[f] = json.load(file)
    return data

def read_yaml(path):
    """YAML 파일 읽기"""
    with open(path) as f:
        return yaml.safe_load(f)

# -------------------------
# YAML 검증
# -------------------------
def check_yaml_integrity(file_path):
    """config YAML 유효성 체크 (division 필수)"""
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
    ONTAP volume 정보 기반으로
    FSA 스캔 대상 객체(scan_objects) 생성
    """

    logger.info("[START] get_scan_objects")

    scan_objects = []
    division = config.get("division", [])

    for cluster in data:
        try:
            cluster_info = cluster["cluster"]

            for volume in cluster["msg"]["records"]:
                name = volume.get("volume")
                path = volume.get("junction_path")
                uuid = volume.get("instance_uuid")
                analytics = volume.get("analytics_state")

                # junction_path 없거나 analytics off면 제외
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
# USER 디렉토리 탐색 + 사용량 수집
# -------------------------
def find_and_collect_usage(scan_objects):
    """
    BFS 방식으로 디렉토리 탐색하여
    target 디렉토리(USER 등) 찾고
    하위 디렉토리 usage 수집
    """

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

        queue = deque([("/", 1)])  # BFS 시작
        visited = set()
        found_roots = set()

        while queue:
            path, depth = queue.popleft()

            # 최대 depth 제한 + 방문 체크
            if depth > 7 or path in visited:
                continue

            visited.add(path)

            try:
                encoded_path = quote(path if path else "/", safe="")
                url = f"{base_url}/{encoded_path}"

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

                for r in records:
                    name = r.get("name")
                    parent = r.get("path") or "/"
                    r_type = r.get("type")

                    # 불필요 디렉토리 제외
                    if name in [".", "..", ".snapshot"]:
                        continue

                    if r_type != "directory":
                        continue

                    full_path = f"{parent.rstrip('/')}/{name}"

                    # target 디렉토리 발견
                    if name in targets:

                        if full_path in found_roots:
                            continue

                        found_roots.add(full_path)

                        # 하위 디렉토리 usage 조회
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

                        sub_records = res2.json().get("records", [])

                        for sr in sub_records:
                            sub_name = sr.get("name")
                            sub_parent = sr.get("path") or full_path

                            if sub_name in [".", "..", ".snapshot"]:
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

                    # BFS 확장
                    queue.append((full_path, depth + 1))

            except Exception as e:
                logger.error(f"[ERROR] path={path} {str(e)}")

    logger.info(f"[END] find_and_collect_usage result_count={len(results)}")
    return results

# -------------------------
# 사용자 정보 조회 (finger2)
# -------------------------
def get_user_info(owner_id):
    """owner_id → 사용자 이름 / 이메일 조회"""
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
    """email 기준으로 데이터 그룹핑"""
    grouped = {}

    for d in data:
        email = d.get("email", "unknown")

        if email not in grouped:
            grouped[email] = []

        grouped[email].append(d)

    return grouped

# -------------------------
# HTML 생성 (공통 템플릿)
# -------------------------
def build_html(data):
    """관리자/사용자 공통 HTML 생성"""

    html = """<html><head><meta charset="UTF-8"></head><body>
    <h2>Directory Usage Report</h2>
    <table border="1">
    <tr>
        <th>Division</th><th>Volume</th><th>User Dir</th>
        <th>User Name</th><th>Email</th><th>Usage (GB)</th>
    </tr>"""

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
        </tr>"""

    html += "</table></body></html>"

    return html

# -------------------------
# main
# -------------------------
def main():
    """request 타입에 따라 기능 분기"""

    try:
        if args.request == "get_scan_object":
            data = read_json(args.file)
            config = check_yaml_integrity(args.config)
            result = get_scan_objects(data[args.file[0]], config)
            print(yaml.safe_dump(result))

        elif args.request == "find_and_collect_usage":
            data = read_yaml(args.file[0])
            result = find_and_collect_usage(data)
            print(yaml.safe_dump(result))

        elif args.request == "build_all_mail":
            data = read_yaml(args.file[0])

            total_html = build_html(data)
            grouped = group_by_user(data)

            result = {
                "total_html": total_html,
                "users": []
            }

            for email, items in grouped.items():
                result["users"].append({
                    "email": email,
                    "html": build_html(items)
                })

            print(yaml.safe_dump(result))

        else:
            logger.error(f"invalid request: {args.request}")

    except Exception:
        logger.error(traceback.format_exc())
        print(traceback.format_exc(), file=sys.stderr)

if __name__ == "__main__":
    main()