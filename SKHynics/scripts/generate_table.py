#!/usr/bin/env python3
import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import argparse
import pandas
import json
import yaml
parser = argparse.ArgumentParser(description="Please refenace Netapp AIQUM doc : https://docs.netapp.com/us-en/active-iq-unified-manager/events/concept_how_scripts_work_with_alerts.html")
parser.add_argument("-f", "--file", type=str, help="read filename",required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
args= parser.parse_args()

# JSON 파일로부터 데이터를 읽어옵니다.
json_file = args.file
with open(json_file, 'r') as file:
    data = json.load(file)

# Pandas DataFrame을 생성합니다.
datatable = pandas.DataFrame()

def storage_inode_report_by_volume(data):

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
    json_file = args.file
    with open(json_file, 'r') as file:
        data = json.load(file)
    inode_total=0
    inode_used=0
    for volume in data["ontap_info"]["storage/volumes"]["records"]:
        inode_total= inode_total+volume["files"]["maximum"]
        inode_used= inode_used+volume["files"]["used"]

    add=pandas.DataFrame.from_records([{
        'cluster name': volume["name"],
        'Total Inodes': inode_total,
        'Used Inodes': inode_used, 
        'Free Inodes': volume["files"]["maximum"] - volume["files"]["used"],
        'Inode Use%': round(volume["files"]["used"] / volume["files"]["maximum"] * 100,2)
    }])
    datatable=datatable._append(add,ignore_index = True)

# HTML 테이블로 변환합니다.
html = """\
<html>
  <head></head>
  <body>
    {0}
  </body>
</html>
""".format(datatable.to_html(index=False))

# 표준 출력으로 HTML 테이블을 출력합니다.
print(html)
