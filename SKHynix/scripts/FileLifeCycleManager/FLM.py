#!/usr/bin/env python3
# 2024 05 02
import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import argparse
import pandas
import json
import logging
import traceback
import yaml
import re
parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
parser.add_argument("-f", "--file", type=str, nargs='+', help="read filenames example: -f filename1 filename2", required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
parser.add_argument("--config", type=str, help="config.yaml",required=True)
args= parser.parse_args()
# logger
logger = logging.getLogger(name='flm_log')
logger.setLevel(logging.DEBUG) ## 경고 수준 설정
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
## 스트림헨들러로 콘솔에 출력
# stream_handler = logging.StreamHandler() ## 스트림 핸들러 생성
# stream_handler.setFormatter(formatter) ## 텍스트 포맷 설정
# logger.addHandler(stream_handler) ## 핸들러 등록
## 파일 핸들러로 파일에 남김
file_handler = logging.FileHandler('flm.log', mode='a') ## 파일 핸들러 생성
file_handler.setFormatter(formatter) ## 텍스트 포맷 설정
logger.addHandler(file_handler) ## 핸들러 등록

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
                    'vol_name_regexp': str,
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
    
    result = validate_structure(config, required_structure)
    if result != True:
        return f"Validation error: {result}"
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
                if not svm_name:
                    logger.debug(f"{cluster['cluster']['name']} svm.name key가 비어 있습니다.")
                if not export_policy:
                    logger.debug(f"{cluster['cluster']['name']} nas.export_policy.name key가 비어 있습니다.")
                if not path:
                    logger.debug(f"{cluster['cluster']['name']} nas.path key가 비어 있습니다.")

                # Check if the volume should be excluded
                if any(ex['name'] == name for ex in exclude):
                    continue

                # Check if volume matches any division criteria
                for div in division:
                    vol_name_regexp = div['vol_name_regexp']
                    exportpolicy_names = [exp['name'] for exp in div['exportpolicy']]
                    
                    # Check if volume name matches the regexp or export policy names
                    if re.search(vol_name_regexp, name) or export_policy in exportpolicy_names:
                        scan_objects.append({
                            'mount_path': f"{svm_name}.{datacenter}.{domain}:{path}",
                            'div' : f"{div['name']}"
                            }
                        )
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
    config = check_yaml_integrity(args.config)
    print(get_scan_objects(data[args.file[0]],config))
    # test.
    # read_the_file_and_save_metrics(files,args.output_json_file_path,includelist,excludelist)

if __name__ == "__main__":
    main()