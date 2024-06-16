#!/usr/bin/env python3
# 2024 05 02
import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import argparse
import json
import logging
import traceback
import yaml
import re
import os
parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
parser.add_argument("-f", "--file", type=str, nargs='+', help="read filenames example: -f filename1 filename2", required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
parser.add_argument("--config", type=str, help="config.yaml",required=True)
args= parser.parse_args()

# 사용자 홈 디렉토리 경로 얻기
home_dir = os.path.expanduser("~")
log_dir = os.path.join(home_dir, "logs")

# 로그 디렉토리가 존재하지 않으면 생성
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 로그 파일 경로 설정
log_file_path = os.path.join(log_dir, "DLC.log")

# 로거 설정
logger = logging.getLogger('DLC')
logger.setLevel(logging.DEBUG)  # 로그 레벨 설정

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
data={}
for json_file in args.file:
    with open(json_file, 'r') as file:
        data[json_file] = json.load(file)

def check_yaml_integrity(file_path):
    required_structure = {
        'config': {
            'domain': str,
            'division': [
                {
                    'name': str,
                    'exportpolicy': [{'name': str}]
                }
            ],
            'exclude': [{'name': str}]
        }
    }
    # YAML 파일 로드
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"validate error: reading YAML file: {e}")
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
            print(f"Validation error: {vol_name_regexp} 정규식 표현이 유효하지 않습니다.")
            return False

    result = validate_structure(config, required_structure)
    if result != True:
        # 정규식 표현 검증
        for division in config['config']['division']:
            if 'vol_name_regexp' in division:
                vol_name_regexp = division['vol_name_regexp']
            else:
                vol_name_regexp = ".*"
            if not check_regex(vol_name_regexp):
                exit

        logger.error(f"Validation error: {result}")
        print(f"Validation error: {result}")
        exit
    else:
        return config
    
def get_scan_objects(data,config):
    scan_objects =[]
    # Extract configuration details
    domain = config['config']['domain']
    division = config['config']['division']
    exclude = config['config']['exclude']
    
    for cluster in data:
        try:
            datacenter = cluster["cluster"]["datacenter"]
            for volume in cluster["ontap_info"]["storage/volumes"]["records"]:
                svm_name = volume["svm"]["name"] if "name" in volume["svm"] else ""
                export_policy = volume["nas"]["export_policy"]["name"] if "export_policy" in volume["nas"] and "name" in volume["nas"]["export_policy"] else ""
                path = volume["nas"]["path"] if "path" in volume["nas"] else ""
                name = volume["name"]
                cluster_name = cluster['cluster']['name']
                if not svm_name:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼룸의 svm.name key가 비어 있습니다.")
                if not export_policy:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼룸의 nas.export_policy.name key가 비어 있습니다.")
                if not path:
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼룸의 nas.path key가 비어 있습니다.")

                # Check if the volume should be excluded
                if any(ex['name'] == name for ex in exclude):
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼룸을 목록에서 제외합니다.")
                    continue
                elif path == "":
                    logger.debug(f"{cluster['cluster']['name']} {name} 볼룸을 목록에서 제외합니다.")
                    continue            

                # Check if volume matches any division criteria
                for div in division: 
                    if 'vol_name_regexp' in div: 
                        vol_name_regexp = div['vol_name_regexp']
                    else:
                        vol_name_regexp = ".*"
                    exportpolicy_names = [exp['name'] for exp in div['exportpolicy']]
                    if not svm_name:
                        logger.debug(f"{div['name']} 의 vol_name_regexp key가 비어 있습니다.")

                    if 'searchdir' in div:
                        for string in div['searchdir']:
                            searchdir =  searchdir+" "+string
                    else:
                        searchdir = None

                    # Check if volume name matches the regexp or export policy names
                    if re.search(vol_name_regexp, name) and export_policy in exportpolicy_names:
                        if datacenter == "test":
                            scan_objects.append({
                                'volume' : name,
                                'mount_path': f"{svm_name}.{domain}:{path}",
                                'div' : f"{div['name']}",
                                'export_policy': f"{export_policy}",
                                'xcp_option':div['xcp_option'],
                                'autopath': div['autopath'],
                                'searchdir': div['searchdir']
                                }
                            )
                            logger.debug(f"{datacenter}, {cluster['cluster']['name']} {name} 볼룸 목록에 추가합니다.")
                        elif datacenter == "nkic":
                            scan_objects.append({
                                'volume' : name,
                                'mount_path': f"{svm_name}.nkic.{domain}:{path}",
                                'div' : f"{div['name']}",
                                'export_policy': f"{export_policy}",
                                'xcp_option':div['xcp_option'],
                                'autopath': div['autopath'],
                                'searchdir': div['searchdir']
                                }
                            )
                            logger.debug(f"{datacenter}, {cluster['cluster']['name']} {name} 볼룸 목록에 추가합니다.")
                        else:
                            scan_objects.append({
                                'volume' : name,
                                'mount_path': f"{cluster_name}.{domain}:{path}",
                                'div' : f"{div['name']}",
                                'export_policy': f"{export_policy}",
                                'xcp_option': div['xcp_option'],
                                'autopath': div['autopath'],
                                'searchdir': div['searchdir']
                                }
                            )
                            logger.debug(f"{datacenter}, {cluster['cluster']['name']} {name} 볼룸 목록에 추가합니다.")
                    else:
                        logger.debug(f"allow exportpolicy list: {exportpolicy_names}")
                        logger.debug(f"정규식 && exportpolicy 가 일치하지 않습니다. datacenter : {datacenter}, cluster_name: {cluster['cluster']['name']}, volume_name: {name}, vol_name_regexp: {vol_name_regexp}, export_policy: {export_policy}")

        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"KeyError: {e} - {cluster['cluster']['name']}",traceback.format_exc())
        except Exception as e:
            logger.error(traceback.format_exc())
            print("Error:" ,traceback.format_exc())
    return scan_objects

def main():
    # cURL command's target URL
    # url = 'http://10.10.242.101:12993/metrics'  # Replace with your actual URL
    # 무결성 검사 실행
    try:
        if args.request == "get_scan_object":
            config = check_yaml_integrity(args.config)
            print(get_scan_objects(data[args.file[0]],config))
            logger.info("print success")        
        else:
            logger.error(args.request+" request is not matched")
            print(args.request+" request is not matched")

    except Exception as e:
        print("Error:" ,traceback.format_exc())
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()

