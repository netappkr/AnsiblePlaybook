#!/usr/bin/env python3
# 2024 05 02
import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import argparse
import pandas
import json
import logging
import traceback
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