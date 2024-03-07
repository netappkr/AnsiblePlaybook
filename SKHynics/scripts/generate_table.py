#!/usr/bin/env python3
import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import argparse
import pandas
import json
import logging
import traceback
parser = argparse.ArgumentParser(description="Please refenace Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
parser.add_argument("-f", "--file", type=str, help="read filename",required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
args= parser.parse_args()

# logger
logger = logging.getLogger(name='generate_table_log')
logger.setLevel(logging.INFO) ## 경고 수준 설정
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
## 스트림헨들러로 콘솔에 출력
# stream_handler = logging.StreamHandler() ## 스트림 핸들러 생성
# stream_handler.setFormatter(formatter) ## 텍스트 포맷 설정
# logger.addHandler(stream_handler) ## 핸들러 등록
## 파일 핸들러로 파일에 남김
file_handler = logging.FileHandler('generate_table.log', mode='w') ## 파일 핸들러 생성
file_handler.setFormatter(formatter) ## 텍스트 포맷 설정
logger.addHandler(file_handler) ## 핸들러 등록

# JSON 파일로부터 데이터를 읽어옵니다.
json_file = args.file
with open(json_file, 'r') as file:
    data = json.load(file)

# Pandas DataFrame을 생성합니다.
datatable = pandas.DataFrame()


def storage_inode_report_by_volume(data):
    global datatable
    for volume in data["ontap_info"]["storage/volumes"]["records"]:
        add=pandas.DataFrame.from_records([{
            'Volume Name': volume["name"],
            'Total Inodes': volume["files"]["maximum"],
            'Used Inodes': volume["files"]["used"], 
            'Free Inodes': volume["files"]["maximum"] - volume["files"]["used"],
            'Inode Use%': round(volume["files"]["used"] / volume["files"]["maximum"] * 100,2)
        }])
        
        datatable=datatable._append(add,ignore_index = True)

def storage_inode_report_by_cluster(data):
    global datatable
    for cluster in data:
        inode_total=0
        inode_used=0
        for volume in cluster["ontap_info"]["storage/volumes"]["records"]:
            inode_total= inode_total+volume["files"]["maximum"]
            inode_used= inode_used+volume["files"]["used"]

        add=pandas.DataFrame.from_records([{
            'cluster name': cluster["cluster"]["name"],
            'Total Inodes': inode_total,
            'Used Inodes': inode_used, 
            'Free Inodes': inode_total - inode_used,
            'Inode Use%': round(inode_used / inode_total * 100,2)
        }])
        datatable=datatable._append(add,ignore_index = True)

def storage_space_report_by_cluster(data):
    global datatable
    for cluster in data:
        total_size=0
        used_size=0
        for volume in cluster["ontap_info"]["storage/aggregates"]["records"]:
            total_size= total_size+volume["space"]["block_storage"]["size"]
            used_size= used_size+volume["space"]["block_storage"]["used"]
            

        add=pandas.DataFrame.from_records([{
            'cluster name': cluster["cluster"]["name"],
            'Total Size(TiB)': round(total_size/1024/1024/1024/1024,2),
            'Used Size(TiB)': round(used_size/1024/1024/1024/1024,2), 
            'Free Size(TiB)': round((total_size - used_size)/1024/1024/1024/1024,2),
            'Used Rate(%)': round(used_size / total_size * 100,2)
        }])
        datatable=datatable._append(add,ignore_index = True)
        
def main():
    try:
        if args.request == "clusters_indoe_info":
            storage_inode_report_by_cluster(data)
        elif args.request == "volume_indoe_info":
            storage_inode_report_by_volume(data)
        elif args.request == "clusters_space_info":
            storage_space_report_by_cluster(data)
        else:
            logger.error(args.request+" request is not matched")

        # HTML 테이블로 변환합니다.
        html = """\
        <html>
        <head></head>
        <body>
        <p>{1}</p>
        {0}
        </body>
        </html>
        """.format(datatable.to_html(index=False),args.request)

        # 표준 출력으로 HTML 테이블을 출력합니다.
        print(html)
    except Exception as e:
        print("Error:" ,traceback.format_exc())
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    main()

