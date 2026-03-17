#!/usr/bin/env python3
import requests
import urllib3
from urllib.parse import quote
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import argparse
import json
import logging
import traceback
import yaml
import re
import os
import sys
parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
parser.add_argument("-f", "--file", type=str, nargs='+', help="read filenames example: -f filename", required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
parser.add_argument("--config", type=str, help="config.yaml",required=False)
args= parser.parse_args()

# 사용자 홈 디렉토리 경로 얻기
home_dir = os.path.expanduser("~")
log_dir = os.path.join(home_dir, "logs")

# 로그 디렉토리가 존재하지 않으면 생성
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 로그 파일 경로 설정
log_file_path = os.path.join(log_dir, ".log")

# 로거 설정
logger = logging.getLogger('fsa')
logger.setLevel(logging.INFO)  # 로그 레벨 설정

# 로그 포맷 설정
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 파일 핸들러 설정
file_handler = logging.FileHandler(log_file_path, mode='a')  # 파일 경로를 정확하게 지정
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 선택적으로 콘솔 로그 출력
# stream_handler = logging.StreamHandler()
# stream_handler.setFormatter(formatter)
# logger.addHandler(stream_handler)

# JSON 파일로부터 데이터를 읽어옵니다.

def read_json(filelist):
    data={}
    for json_file in filelist:
        with open(json_file, 'r') as file:
            data[json_file] = json.load(file)
    return data

def read_yaml_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise ValueError("YAML structure must be list or dict")

        return data

    except Exception:
        logger.error(traceback.format_exc())
        print("Error reading YAML:", traceback.format_exc(), file=sys.stderr)
        return None


def check_yaml_integrity(file_path):
    required_structure = {
        'division': [
            {
                'name': str
            }
        ]
    }
    # YAML 파일 로드
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"validate error: reading YAML file: {e}")
        print(f"Validation error: reading YAML file: {e}",file=sys.stderr)
        exit

    # 필수 키 및 구조 검증
    def validate_structure(data, structure):
        if not isinstance(data, dict):
            return "Data is not a dictionary"

        for key, value_type in structure.items():
            if isinstance(value_type, list):
                if key not in data:
                    return f"Missing key {key}"
                if not isinstance(data[key], list):
                    return f"Key '{key}' must be a list"
                for item in data[key]:
                    result = validate_structure(item, value_type[0])
                    if result != True:
                        return result
            elif isinstance(value_type, dict):
                if key not in data:
                    return f"Missing key {key}"
                result = validate_structure(data[key], value_type)
                if result != True:
                    return result
            else:
                if key not in data or not isinstance(data[key], value_type):
                    return f"Key '{key}' must be a {value_type.__name__}"
        return True
    
    def check_regex(regexp):
        try:
            re.compile(regexp)
            return True
        except re.error:
            logger.error(f"Validation error: {vol_name_regexp} 정규식 표현이 유효하지 않습니다.")
            print(f"Validation error: {vol_name_regexp} 정규식 표현이 유효하지 않습니다.",file=sys.stderr)
            return False

    result = validate_structure(config, required_structure)
    if result != True:
        # 정규식 표현 검증
        for division in config['division']:
            if 'vol_name_regexp' in division:
                vol_name_regexp = division['vol_name_regexp']
            else:
                vol_name_regexp = ".*"
            if not check_regex(vol_name_regexp):
                exit

        logger.error(f"Validation error: {result}")
        print(f"Validation error: {result}",file=sys.stderr)
        exit
    else:
        return config
    
def get_scan_objects(data,config):
    scan_objects =[]
    # Extract configuration details
    domain = config['domain']
    division = config['division']
    exclude = config['exclude'] if "exclude" in config else None
    for cluster in data:
        try:
            datacenter = cluster["cluster"]["datacenter"]
            for volume in cluster["msg"]["records"]:
                svm_name = volume["vserver"] if "vserver" in volume else ""
                export_policy = volume["policy"]if "policy" in volume else ""
                path = volume["junction_path"] if "junction_path" in volume else ""
                name = volume["volume"]
                cluster_name = cluster['cluster']['name']
                vol_uuid = volume["uuid"]
                analytics = volume["analytics_state"] if "analytics_state" in volume else ""

                if not svm_name:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼륨의 vserver key가 비어 있습니다.")
                if not export_policy:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼륨의 policy key가 비어 있습니다.")
                if not path:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼륨의 junction_path key가 비어 있습니다.")
                if not analytics:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼륨의 analytics_state key가 비어 있습니다.")
                # Check if the volume should be excluded
                if exclude in config:
                    if any(ex['vol_name'] == name for ex in exclude):
                        logger.info(f"matched exclude vol name policy , {cluster['cluster']['name']} {name} 볼륨을 목록에서 제외합니다.")
                        continue
                if path == "":
                    logger.info(f"path: {path}, {cluster['cluster']['name']} {name} 볼륨을 목록에서 제외합니다.")
                    continue
                if analytics != "on":            
                    logger.info(f"analytics: {analytics}, {cluster['cluster']['name']} {name} 볼륨을 목록에서 제외합니다.")
                    continue
                # Check if volume matches any division criteria
                for div in division:
                    if 'searchdir' in div:
                        search_dirs_str = ' '.join(div['searchdir'])
                    else:
                        search_dirs_str = None

                    # Check if volume name matches the regexp or export policy names
                    if "fsa_option" in div:
                        if datacenter == "test":
                            scan_objects.append({
                                'cluster': cluster['cluster'],
                                'volume' : name,
                                "vol_uuid": vol_uuid,
                                'mount_path': f"{svm_name}.{domain}:{path}",
                                'div' : f"{div['name']}",
                                'export_policy': f"{export_policy}",
                                'fsa_option':div['fsa_option'],
                                'searchdir': search_dirs_str
                                }
                            )
                            logger.debug(f"{datacenter}, {cluster['cluster']['name']} {name} 볼륨 목록에 추가합니다.")
                        elif datacenter == "nkic":
                            scan_objects.append({
                                'cluster': cluster['cluster'],
                                'volume' : name,
                                "vol_uuid": vol_uuid,
                                'mount_path': f"{svm_name}.nkic.{domain}:{path}",
                                'div' : f"{div['name']}",
                                'export_policy': f"{export_policy}",
                                'fsa_option':div['fsa_option'],
                                'searchdir': search_dirs_str
                                }
                            )
                            logger.debug(f"{datacenter}, {cluster['cluster']['name']} {name} 볼륨 목록에 추가합니다.")
                        else:
                            scan_objects.append({
                                'cluster': cluster['cluster'],
                                'volume' : name,
                                "vol_uuid": vol_uuid,
                                'mount_path': f"{cluster_name}.{domain}:{path}",
                                'div' : f"{div['name']}",
                                'export_policy': f"{export_policy}",
                                'fsa_option': div['fsa_option'],
                                'searchdir': search_dirs_str
                                }
                            )
                            logger.debug(f"{datacenter}, {cluster['cluster']['name']} {name} 볼륨 목록에 추가합니다.")
                    else:
                        logger.info(f"fsa_option 이 비어있습니다., {cluster['cluster']['name']} {name} 볼륨을 목록에서 제외합니다.")
                        logger.debug(f"fsa_option 이 비어있습니다.. datacenter : {datacenter}, cluster_name: {cluster['cluster']['name']}, volume_name: {name}")

        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"KeyError: {e} - {cluster['cluster']['name']}",traceback.format_exc())
        except Exception as e:
            logger.error("func get_scan_objects:",traceback.format_exc())
            print("func get_scan_objects Error:" ,traceback.format_exc(),file=sys.stderr)
    return scan_objects


from collections import defaultdict

def call_fsa_api(scan_objects):

    session = requests.Session()
    session.verify = False
    session.headers.update({"Accept": "application/json"})

    all_files = []
    summary = {
        "division": defaultdict(lambda: {"used": 0, "count": 0}),
        "volume": defaultdict(lambda: {"used": 0, "count": 0}),
        "directory": defaultdict(lambda: {"used": 0, "count": 0})
    }

    scan_status = []

    for obj in scan_objects:
        cluster = obj["cluster"]
        volume_uuid = obj["vol_uuid"]
        fsa_option = obj["fsa_option"]
        div = obj["div"]
        volume_name = obj["volume"]
        

        base_url = f"https://{cluster['ip']}/api/storage/volumes/{volume_uuid}/files"
        auth = (cluster["ID"], cluster["PW"])

        for path_item in fsa_option.get("path", []):
            directory = path_item["dir"] if "dir" in path_item["dir"] else ""
            file_filter = path_item["file"] if "file" in path_item["file"] else ""

            encoded_path = quote(directory, safe="")
            url = f"{base_url}/{encoded_path}"

            params = {
                "type": fsa_option.get("type"),
                "analytics.bytes_used": fsa_option.get("analytics_bytes_used"),
                "fields": "size,name,path,modified_time,analytics.bytes_used",
                "return_records": "true",
                "return_timeout": 30
            }

            try:
                while url:
                    response = session.get(url, auth=auth, params=params)
                    response.raise_for_status()
                    data = response.json()

                    records = data.get("records", [])

                    for r in records:
                        size = r.get("size", 0)

                        # 파일 개별 기록
                        all_files.append({
                            "cluster": cluster["name"],
                            "division": div,
                            "volume": volume_name,
                            "dir": directory,
                            "file": r.get("name"),
                            "size": size,
                            "modified_time": r.get("modified_time")
                        })
                        summary = {
                            "division": {},
                            "volume": {},
                            "directory": {}
                        }
                        # division
                        if div not in summary["division"]:
                            summary["division"][div] = {"used": 0, "count": 0}

                        summary["division"][div]["used"] += size
                        summary["division"][div]["count"] += 1

                        # volume
                        if div not in summary["division"]:
                            summary["division"][div] = {"used": 0, "count": 0}

                        summary["division"][div]["used"] += size
                        summary["division"][div]["count"] += 1

                        # directory
                        if div not in summary["directory"]:
                            summary["directory"][div] = {}

                        if volume_name not in summary["directory"][div]:
                            summary["directory"][div][volume_name] = {}

                        if directory_name not in summary["directory"][div][volume_name]:
                            summary["directory"][div][volume_name][directory_name] = {
                                "used": 0,
                                "count": 0
                            }

                        summary["directory"][div][volume_name][directory_name]["used"] += size
                        summary["directory"][div][volume_name][directory_name]["count"] += 1

                    next_link = data.get("_links", {}).get("next", {}).get("href")
                    if next_link:
                        url = f"https://{cluster['ip']}{next_link}"
                        params = None
                    else:
                        url = None

                scan_status.append({
                    "volume": volume_name,
                    "directory": directory,
                    "status": "SUCCESS"
                })

            except Exception:
                scan_status.append({
                    "volume": volume_name,
                    "directory": directory,
                    "status": "FAILED"
                })
                logger.error(traceback.format_exc())

    return {
        "files": all_files,
        "summary": summary,
        "scan_status": scan_status
    }

def build_mail_report(report_data):

    summary = report_data.get("summary", {})
    scan_status = report_data.get("scan_status", [])

    html = """
    <html>
    <body>
    <h2>FSA Scan Summary Report</h2>
    """

    # ===== Division Summary =====
    html += "<h3>Division Summary</h3>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Division</th><th>Total Used (MB)</th><th>File Count</th></tr>"

    for div, data in summary.get("division", {}).items():
        used_mb = data["used"] / (1024 * 1024)
        html += f"<tr><td>{div}</td><td>{used_mb:.2f}</td><td>{data['count']}</td></tr>"

    html += "</table><br>"

    # ===== Scan Status =====
    html += "<h3>Scan Status</h3>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Volume</th><th>Directory</th><th>Status</th></tr>"

    for item in scan_status:
        color = "green" if item["status"] == "SUCCESS" else "red"
        html += f"<tr><td>{item['volume']}</td><td>{item['directory']}</td><td style='color:{color}'>{item['status']}</td></tr>"

    html += "</table>"

    html += "</body></html>"

    return html

def main():
    # cURL command's target URL
    # url = 'http://10.10.242.101:12993/metrics'  # Replace with your actual URL
    # 무결성 검사 실행
    try:
        if args.request == "get_scan_object":
            data = read_json(args.file)
            config = check_yaml_integrity(args.config)
            if config:
                print(json.dumps(get_scan_objects(data[args.file[0]],config)))
            logger.info("print success")

        elif args.request == "get_fsa_data":
            scan_objects = read_yaml_file(args.file[0])

            if not scan_objects:
                return

            fsa_results = call_fsa_api(scan_objects)
            print(
                yaml.safe_dump(
                    fsa_results,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False
                )
            )
            logger.info("print success")
        elif args.request == "build_mail":
            report = read_yaml_file(args.file[0])
            html = build_mail_report(report)
            print(f"Mail HTML saved to {path}")

        else:
            logger.error(args.request+" request is not matched")
            print(args.request+" request is not matched")

    except Exception as e:
        print("Error:" ,traceback.format_exc(),file=sys.stderr)
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()

