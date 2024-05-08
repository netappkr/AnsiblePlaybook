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

def check_yaml_integrity(file_path):
    required_structure = {
        'exportpolicy': {
            'name': str
        },
        'kind': {
            'division': str
        }
    }
    # YAML 파일 로드
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
    except Exception as e:
        logger.error(f"validate error: reading YAML file: {e}")
        return f"Error reading YAML file: {e}"
        # 필수 키 및 구조 검증

    def validate_structure(data, structure):
        if not isinstance(data, dict):
            logger.error(f"validate error: data is not a dictionary check the config.yaml")
            return f"Data is not a dictionary"

        for key, value_type in structure.items():
            if isinstance(value_type, dict):
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
        return f"validate error: {result}"
    else:
        return config

def main():
    # cURL command's target URL
    # url = 'http://10.10.242.101:12993/metrics'  # Replace with your actual URL
    # 무결성 검사 실행
    print(check_yaml_integrity(args.config))
    # test.
    # read_the_file_and_save_metrics(files,args.output_json_file_path,includelist,excludelist)

if __name__ == "__main__":
    main()