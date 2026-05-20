
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
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from collections import deque
from urllib.parse import quote # URL 인코딩
import collections
import subprocess
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
parser.add_argument("--auto-db", type=str, help="auto_db.yaml path")
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
    config:
        autopath:
            - sim
            - library

        exportpolicy:
            - name: "default"
            - name: "export-svm_CVO2-vol1"
            - name: "export-svm_CVO2-vol2"
        fsa_option:
            type: directory
            analytics_bytes_used: ">=1M"
            listdir:
            - dir: CAE
            - dir: SCH
            - dir: LAY
            - dir: dir1/dir2/CAE
            - dir: dir3/SCH
            path: 
            - dir: USER
            - dir: BE
            - dir: user
            - dir: FE
            - dir: INTERFACE
            - dir: WORK_DIR
            - dir: DK
        cli:                                   
            volumename: "!*spot*,!effi*"
            policy: "!*_ro,!*_ro1,!*exportro*,!no_access"
            type: "rw"
            total: ">=1MB"
            LogicalUsedPercent: ">=4"
    """
    try:
        with open(file_path) as file:
            config = yaml.safe_load(file)

        if "fsa_option" not in config:
            raise ValueError("fsa_option key missing")
        if "autopath" not in config:
            raise ValueError("autopath key missing")

        return config

    except Exception as e:
        logger.error(f"[ERROR] YAML validation: {str(e)}")
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)

# -------------------------
# auto_db.yaml 생성
# -------------------------
def build_auto_yaml_from_file(path):

    data = read_json(path)

    final = {}

    for item in data:
        automap_name = item.get("item")

        if not automap_name:
            continue

        stdout = item.get("stdout", "")

        for line in stdout.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith("="):
                continue

            parts = line.split()

            if len(parts) != 2:
                continue

            alias = parts[0]
            full = parts[1]
            cluster_full = full.split(":")[0]
            cluster = cluster_full.split(".")[0]
            realpath = full.split(":")[-1]
            lookup_key = f"{cluster}:{realpath}"

            final[lookup_key] = {
                "autopath": alias,
                "mountpath": full,
                "autokey": automap_name
            }

            logger.debug(
                f"[AUTO_DB] key={lookup_key}, alias={alias}"
            )

    return final
# -------------------------
# scan object 생성
# -------------------------
def get_scan_objects(data, config):

    logger.info("[START] get_scan_objects")
    scan_objects = []
    cfg = config
    exportpolicy_names = [
        e["name"]
        for e in cfg.get("exportpolicy", [])
    ]

    test_volumes = config.get("test_volume", [])
    auto_map_yaml = {}

    if args.auto_db:
        try:
            auto_map_yaml = read_yaml(args.auto_db) or {}
            logger.info(f"[AUTO MAP] loaded: {args.auto_db}")

        except Exception as e:
            logger.error(f"[ERROR] auto_db load failed: {str(e)}")

    for cluster in data:
        try:
            cluster_info = cluster["cluster"]
            cluster_name = cluster_info.get("name", "unknown")

            for volume in cluster["msg"]["records"]:
                name = volume.get("volume")
                junction_path = volume.get("junction_path")
                svm = volume.get("vserver")
                uuid = volume.get("instance_uuid")
                analytics = volume.get("analytics_state")
                export_policy = volume.get("policy", "")

                # -------------------------
                # 기본 조건
                # -------------------------
                if not junction_path:
                    continue

                if analytics != "on":
                    continue

                # -------------------------
                # export policy filter
                # -------------------------
                if export_policy not in exportpolicy_names:
                    logger.debug(
                        f"[SKIP] export policy mismatch "
                        f"volume={name}, policy={export_policy}"
                    )
                    continue

                # -------------------------
                # test volume filter
                # -------------------------
                if test_volumes and name not in test_volumes:
                    logger.debug(
                        f"[SKIP] test_volume mismatch volume={name}"
                    )
                    continue

                # -------------------------
                # auto_db lookup
                # key:
                # nsim2m14:/sim_nand_he1ttlcdv
                # -------------------------
                lookup_key = f"{cluster_name}:{junction_path}"

                logger.debug(f"[LOOKUP] key={lookup_key}")

                auto_info = auto_map_yaml.get(lookup_key)

                auto_alias = name
                mountpath = None
                automap_key = None

                if auto_info:

                    auto_alias = auto_info.get(
                        "autopath",
                        name
                    )

                    mountpath = auto_info.get(
                        "mountpath"
                    )

                    automap_key = auto_info.get(
                        "autokey"
                    )

                    logger.debug(
                        f"[AUTO MAP HIT] "
                        f"volume={name}, "
                        f"alias={auto_alias}, "
                        f"automap={automap_key}"
                    )

                else:

                    logger.debug(
                        f"[AUTO MAP MISS] "
                        f"lookup_key={lookup_key}"
                    )

                svm_domain = None

                if mountpath:
                    svm_domain = mountpath.split(":")[0]

                scan_objects.append({
                    "cluster": cluster_info,
                    "vserver": svm,
                    "svm_domain": svm_domain,
                    "volume": name,
                    "vol_uuid": uuid,
                    "junction_path": junction_path,
                    "auto_alias": auto_alias,
                    "automap": automap_key,
                    "fsa_option": cfg["fsa_option"]
                })

                logger.debug(
                    f"[ADD] volume={name}, "
                    f"alias={auto_alias}, "
                    f"automap={automap_key}"
                )

        except Exception:
            logger.error(traceback.format_exc())

    logger.info(
        f"[END] get_scan_objects count={len(scan_objects)}"
    )

    return scan_objects


# -------------------------
# USER 디렉토리 찾기 + 사용량 수집
# -------------------------
def find_and_collect_usage(scan_objects, usage_latest_path):

    logger.info(f"[START] find_and_collect_usage count={len(scan_objects)}")

    # -----------------------
    # 이전 데이터 로딩
    # -----------------------
    prev_map = {}

    try:

        if usage_latest_path and os.path.exists(usage_latest_path):
            prev_data = read_yaml(usage_latest_path)
            if not prev_data:
                logger.warning(
                    f"[WARN] empty previous file: {usage_latest_path}"
                )
                prev_data = []

            for d in prev_data:
                try:
                    volume = d.get("volume")
                    key = d.get("full_path")
                    used = d.get("bytes_used", 0)

                    if not key:
                        continue

                    if not isinstance(used, (int, float)):
                        used = 0

                    if volume not in prev_map:
                        prev_map[volume] = {}

                    prev_map[volume][key] = used

                except Exception as e:
                    logger.warning(
                        f"[WARN] invalid record skipped: {str(e)}"
                    )

        else:
            logger.info("[FIRST RUN] no previous file")

    except Exception as e:
        logger.error(
            f"[ERROR] failed to load previous data: {str(e)}"
        )

    logger.debug("[prev_map]")
    logger.debug(
        json.dumps(prev_map, indent=2, ensure_ascii=False)
    )

    # -----------------------
    # requests session
    # -----------------------
    session = requests.Session()
    session.verify = False

    results = []

    # -----------------------
    # scan object loop
    # -----------------------
    for obj in scan_objects:

        try:

            cluster = obj["cluster"]
            base_url = (
                f"https://{cluster['ip']}"
                f"/api/storage/volumes/{obj['vol_uuid']}/files"
            )
            auth = (
                cluster["ID"],
                cluster["PW"]
            )
            logger.info(
                f"[SEARCH] volume={obj['volume']}"
            )

            # -----------------------
            # filter
            # -----------------------
            filter_expr = obj["fsa_option"].get(
                "analytics_bytes_used"
            )
            if filter_expr:
                op, threshold = parse_size_filter(
                    filter_expr
                )

            # -----------------------
            # inventory config
            # -----------------------
            listdir_targets = set(
                d["dir"].split("/")[-1]
                for d in obj["fsa_option"].get("listdir", [])
            )

            path_targets = set(
                d["dir"]
                for d in obj["fsa_option"].get("path", [])
            )

            logger.debug(
                f"[LISTDIR TARGETS] {listdir_targets}"
            )

            logger.debug(
                f"[PATH TARGETS] {path_targets}"
            )

            # ==================================================
            # STEP 1
            # ROOT(/) 조회
            # ==================================================
            root_url = f"{base_url}/%2F"
            logger.debug(
                f"[ROOT SEARCH] {root_url}"
            )
            root_res = session.get(
                root_url,
                auth=auth,
                params={
                    "type": "directory",
                    "fields": "name,path,type"
                },
                timeout=30
            )
            root_res.raise_for_status()
            root_records = root_res.json().get(
                "records",
                []
            )

            # ==================================================
            # STEP 2
            # listdir 발견
            # ==================================================
            found_listdirs = []
            for r in root_records:
                name = r.get("name")
                if name in listdir_targets:
                    full_path = (
                        f"/{name}"
                    )
                    found_listdirs.append(
                        full_path
                    )
                    logger.info(
                        f"[FOUND LISTDIR] {full_path}"
                    )

            # ==================================================
            # STEP 3
            # 발견된 listdir 만 조회
            # ==================================================
            for listdir_path in found_listdirs:
                try:
                    encoded_path = quote(
                        listdir_path,
                        safe=""
                    )
                    url = (
                        f"{base_url}/{encoded_path}"
                    )
                    logger.debug(
                        f"[LISTDIR SEARCH] {url}"
                    )
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
                    records = res.json().get(
                        "records",
                        []
                    )

                    # ==================================================
                    # STEP 4
                    # USER/BE/... 탐색
                    # ==================================================
                    for r in records:
                        name = r.get("name")
                        if name not in path_targets:
                            continue

                        target_path = (
                            f"{listdir_path}/{name}"
                        )

                        logger.info(
                            f"[FOUND TARGET] {target_path}"
                        )

                        # ==================================================
                        # STEP 5
                        # USER 내부 usage 조회
                        # ==================================================
                        encoded_sub = quote(
                            target_path,
                            safe=""
                        )

                        sub_url = (
                            f"{base_url}/{encoded_sub}"
                        )

                        params = {
                            "fields": (
                                "name,"
                                "path,"
                                "owner_id,"
                                "analytics.bytes_used,"
                                "type"
                            )
                        }

                        res2 = session.get(
                            url=sub_url,
                            auth=auth,
                            params=params,
                            timeout=30
                        )

                        res2.raise_for_status()

                        sub_records = res2.json().get(
                            "records",
                            []
                        )

                        # ==================================================
                        # STEP 6
                        # 사용자 디렉토리 usage 수집
                        # ==================================================
                        for sr in sub_records:
                            sub_name = sr.get("name")
                            sub_parent = (
                                sr.get("path")
                                or target_path
                            )
                            sub_type = sr.get("type")

                            if sub_type != "directory":
                                continue

                            used = sr.get(
                                "analytics",
                                {}
                            ).get(
                                "bytes_used",
                                0
                            )

                            # -----------------------
                            # analytics filter
                            # -----------------------
                            if filter_expr:
                                if not check_condition(
                                    used,
                                    op,
                                    threshold
                                ):
                                    continue

                            # -----------------------
                            # diff 계산
                            # -----------------------
                            full_user_path = (
                                f"{sub_parent}/{sub_name}"
                            )

                            prev_used = prev_map.get(
                                obj["volume"],
                                {}
                            ).get(
                                full_user_path,
                                0
                            )

                            diff = (
                                used - prev_used
                            )

                            owner = sr.get(
                                "owner_id"
                            )

                            username, email = (
                                get_user_info(owner)
                            )

                            results.append({
                                "svm_domain":obj.get("svm_domain"),
                                "volume":obj["volume"],
                                "auto_alias":obj.get("auto_alias"),
                                "automap":obj.get("automap"),
                                "user_dir":sub_name,
                                "full_path":full_user_path,
                                "owner_id":owner,
                                "user_name":username,
                                "email":email,
                                "bytes_used":used,
                                "diff_bytes":diff
                            })

                except Exception as e:

                    logger.error(
                        f"[ERROR] listdir_path="
                        f"{listdir_path} "
                        f"{str(e)}"
                    )

        except Exception as e:

            logger.error(
                f"[ERROR] volume={obj['volume']} "
                f"{str(e)}"
            )

    logger.info(
        f"[END] find_and_collect_usage "
        f"result_count={len(results)}"
    )

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
            ["/sw/bin/finger2", str(owner_id)],
            capture_output=True,
            text=True
        )
        logger.debug(f"[FINGER2 OUTPUT] owner_id={owner_id} stdout={res.stdout.strip()}")
        logger.debug(f"[FINGER2 STDERR] owner_id={owner_id} stderr={res.stderr.strip()}")

        name = "unknown"
        email = "unknown"

        for line in res.stdout.splitlines():
            if "Name" in line:
                name = line.split(":")[1].strip()
            if "E-mail" in line:
                email = line.split(":")[1].strip()
        logger.debug(f"[USER PARSED] owner_id={owner_id}, name={name}, email={email}")
        return name, email

    except Exception:
        logger.error(f"[ERROR] Failed to get user info for owner_id={owner_id}")
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
# HTML 생성
# -------------------------
def build_mail(data):

    # volume_map 구조
    # {
    #   volume(alias): {
    #       root(USER/FE): [user data...]
    #   }
    # }
    volume_map = collections.defaultdict(lambda: collections.defaultdict(list))

    for d in data:
        volume = d.get("auto_alias") or d.get("volume")

        # /USER/jeehyun → USER 추출
        root = d["full_path"].rsplit("/", 1)[0]

        volume_map[volume][root].append(d)

    results = []
    logger.debug(f"[VOLUME_MAP] {json.dumps(volume_map, indent=2, ensure_ascii=False)}")
    # -----------------------
    # volume별 메일 생성
    # -----------------------
    for volume, root_map in volume_map.items():

        # -----------------------
        # 이메일 수집 (중복 제거)
        # -----------------------
        email_set = set()
        for roots in root_map.values():
            for d in roots:
                email = d.get("email")
                if email and email != "unknown":
                    email_set.add(email.lower())

        # -----------------------
        # root 정렬
        # -----------------------
        roots = sorted(root_map.keys())

        # 각 root 내부 정렬 (사용량 기준)
        for r in roots:
            root_map[r] = sorted(root_map[r], key=lambda x: x["bytes_used"], reverse=True)

        # 최대 row 길이
        max_len = max(len(root_map[r]) for r in roots)

        # -----------------------
        # HTML 시작
        # -----------------------
        
        sample = next(iter(root_map.values()))[0]
        automap = sample.get("automap")
        alias = sample.get("auto_alias")
        if alias:
            top_path = f"/{automap}/{alias}" 
        else: 
            top_path = f"/{automap}/{volume}"
            logger.debug(f"/{automap}/{volume} is not mapped to alias.")

        html = f"""
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial; background-color:white; color:block; font-size: 12px }}
            table {{ border-collapse: collapse; margin-top: 20px; width:100%; table-layout:fixed }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
            th {{ background-color: #1f2a44; }}
        </style>
        </head>
        <body>

        <h3 style="font-family: Arial, Helvetica, sans-serif;">
            현재 해당 Storage의 사용량이 80% 를 초과하여 사용중이며 현재 상태가 지속될 경우<br>
            Full 발생 및 Data 접근 불가 상황이 예상되오니 아래 내용 참조하시어 빠른 시일 내에 Data 정리 부탁드립니다.<br>
            공용 Storage의 안정적 사용을 위하여 하위 사용 현황 정보 확인 및 Data 삭제 진행 안내드립니다.

        </h3>
        </head>
        <body>

        <table>
        <tr>
            <th colspan="{len(root_map)*3}">{top_path}</th>
        </tr>

        """

        # -----------------------
        # 1행: root header
        # -----------------------
        html += "<tr>"
        for root in roots:
            html += f"<th colspan='3'>{root}</th>"
        html += "</tr>"
        # -----------------------
        # 2행: column header
        # -----------------------
        html += "<tr>"
        for _ in roots:  
            html += """
        <th>Total(GB)</th>
        <th>Dirname</th>
        <th>User</th>
        """
        html += "</tr>"

        # -----------------------
        # 데이터 row
        # -----------------------
        for i in range(max_len):

            html += "<tr>"

            for r in roots:
                items = root_map[r]

                if i < len(items):
                    d = items[i]

                    total_gb = d["bytes_used"] / (1024**3)
                    diff_gb = d["diff_bytes"] / (1024**3)
                    total_format = f"{total_gb:,.0f}"
                    diff_format = f"{diff_gb:,.0f}"

                    # 색상 처리
                    if diff_gb > 0:
                        color = "red"
                        sign = "+"
                    elif diff_gb < 0:
                        color = "deepskyblue"
                        sign = ""
                    else:
                        color = "white"
                        sign = ""
                    username = d.get("user_name", "unknown")
                    if len(username) > 4: # user_name: 홍길동(TL),Hong GilDONG
                        username = username.split(",")[0] # 홍길동(TL)만 표시
                    html += f"""
                    <td>{total_format}</td>
                    <td>{d["user_dir"]}</td>
                    <td>{username}</td>
                    """
                else:
                    # 🔥 빈칸 처리
                    html += """
                    <td></td>
                    <td></td>
                    <td></td>
                    """

            html += "</tr>"

        html += "</table></body></html>"

        results.append({
            "volume": volume,
            "subject": f"{top_path}",
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
            print(yaml.safe_dump(result, sort_keys=False, allow_unicode=True))
        # auto db_yaml 생성
        elif args.request == "build_auto_yaml":
            data = build_auto_yaml_from_file(args.file)
            print(yaml.safe_dump(data, sort_keys=False))

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

