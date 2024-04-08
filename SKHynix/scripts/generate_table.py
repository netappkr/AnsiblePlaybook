#!/usr/bin/env python3
import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import argparse
import pandas
import json
import logging
import traceback
parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
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

def format_with_commas(num):
    return '{0:,}'.format(num)

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
            'description': cluster["cluster"]["description"],
            'Total Inodes': format_with_commas(inode_total),
            'Used Inodes': format_with_commas(inode_used), 
            'Free Inodes': format_with_commas(inode_total - inode_used),
            'Inode Use%': round(inode_used / inode_total * 100)
        }])
        datatable=datatable._append(add,ignore_index = True)
    report_name = "CAD Storage Cluster INODE 사용량 Summary"
    return report_name

def storage_inode_report_by_volume(data):
    global datatable
    for volume in data["ontap_info"]["storage/volumes"]["records"]:
        add=pandas.DataFrame.from_records([{
            'cluster Name': data["cluster"]["name"],
            'Volume Name': volume["name"],
            'Total Inodes': format_with_commas(volume["files"]["maximum"]),
            'Used Inodes': format_with_commas(volume["files"]["used"]), 
            'Free Inodes': format_with_commas(volume["files"]["maximum"] - volume["files"]["used"]),
            'Inode Use%': round(volume["files"]["used"] / volume["files"]["maximum"] * 100)
        }])
        
        datatable=datatable._append(add,ignore_index = True)
    report_name = data["cluster"]["name"] + " Storage Volumes INODE Report"
    return report_name


def storage_space_report_by_cluster(data):
    global datatable
    for cluster in data:
        total_size=0
        used_size=0
        for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
            total_size= total_size+aggr["space"]["block_storage"]["size"]
            used_size= used_size+aggr["space"]["block_storage"]["used"]
            

        add=pandas.DataFrame.from_records([{
            'cluster name': cluster["cluster"]["name"],
            'description': cluster["cluster"]["description"],
            'Total Size(TiB)': format_with_commas(round(total_size/1024/1024/1024/1024,0)),
            'Used Size(TiB)': format_with_commas(round(used_size/1024/1024/1024/1024,0)), 
            'Free Size(TiB)': format_with_commas(round((total_size - used_size)/1024/1024/1024/1024,0)),
            'Used Rate(%)': round(used_size / total_size * 100)
        }])
        datatable=datatable._append(add,ignore_index = True)
    report_name = "CAD Storage Cluster 사용량 Summary"
    return report_name

def storage_space_report_by_aggr(data):
    global datatable
    for aggr in data["ontap_info"]["storage/aggregates"]["records"]:
        total_size=aggr["space"]["block_storage"]["size"]
        used_size=aggr["space"]["block_storage"]["used"]
        
        add=pandas.DataFrame.from_records([{
            'Cluster Name': data["cluster"]["name"],
            'Aggr Name': aggr["name"],
            'Node Name': aggr["home_node"]["name"],
            'Total Size(TiB)': format_with_commas(round(total_size/1024/1024/1024/1024,0)),
            'Used Size(TiB)': format_with_commas(round(used_size/1024/1024/1024/1024,0)), 
            'Free Size(TiB)': format_with_commas(round((total_size - used_size)/1024/1024/1024/1024,0)),
            'Used Rate(%)': round(used_size / total_size * 100)
        }])
        datatable=datatable._append(add,ignore_index = True)
    report_name = "------ Aggregates Capacity Report ------"
    return report_name

def storage_Big_snapshot_report_by_volume(data):
    global datatable
    for cluster in data:
        total_size=0
        used_size=0
        snapshot_used=0
        for volume in cluster["ontap_info"]["storage/volumes"]["records"]:
            total_size= volume["space"]["size"]
            used_size= volume["space"]["used"]
            snapshot_used=volume["space"]["snapshot"]["used"]
            if round(used_size / total_size * 100,2) > 50:
                if snapshot_used > 1099511627776:
                    add=pandas.DataFrame.from_records([{
                        'cluster name': cluster["cluster"]["name"],
                        'volume name' : volume["name"],
                        'volume path' : volume["nas"]["path"],
                        'Total Size(GiB)': format_with_commas(round(total_size/1024/1024/1024,0)),
                        'Used Size(GiB)': format_with_commas(round(used_size/1024/1024/1024,0)), 
                        'Free Size(GiB)': format_with_commas(round((total_size - used_size)/1024/1024/1024,0)),
                        'Used Rate(%)': format_with_commas(round(used_size / total_size * 100,0)),
                        'snaphost Used(Tib)': format_with_commas(round(snapshot_used/1024/1024/1024/1024,0))
                    }])
                    datatable=datatable._append(add,ignore_index = True)
    
def format_html_style(datatable,report_name):
    # HTML 테이블로 변환합니다.
    ## 경고
    # Html 양식의 이메일 제출 시 CSS 포함 전송기능을 지원하지 않는 경우가 있다고 합니다.
    # 이런 경우 방법은 각 Html 항목에 직접 css를 한줄씩 넣어야 합니다.
    datatable=datatable.style.set_caption(report_name)
    datatable=datatable.hide()
    datatable=datatable.set_table_attributes('class="mystyle"')
    # datatable=datatable.style.set_properties(subset=['Total Inodes'], **{'text-align': 'right'})
    html_table= datatable.to_html()
    return html_table
       
def main():
    try:
        if args.request == "clusters_inode_info":
            report_name=storage_inode_report_by_cluster(data)
        elif args.request == "volume_inode_info":
            report_name=storage_inode_report_by_volume(data)
        elif args.request == "clusters_space_info":
            report_name=storage_space_report_by_cluster(data)
        elif args.request == "aggrs_space_info":
            report_name=storage_space_report_by_aggr(data)
        elif args.request == "big_snapshot_info":
            report_name=storage_Big_snapshot_report_by_volume(data)
        else:
            logger.error(args.request+" request is not matched")
            

        # html_table= datatable.render()
        html_table = format_html_style(datatable,report_name)

        # HTML 테이블로 변환합니다.
        ## 경고
        # Html 양식의 이메일 제출 시 CSS 포함 전송기능을 지원하지 않는 경우가 대부분이라고 합니다.
        # 따라서 방법은 각 Html 항목에 직접 css를 한줄씩 넣어야 합니다.
        css = """
        .mystyle {
            font-size: 11pt; 
            font-family: Arial;
            border-collapse: collapse; 
            border: 1px solid silver;

        }

        .mystyle td, th {
            padding: 5px;
            text-align: center;
        }
        .mystyle caption {
            font-size: 16pt;
        }

        .mystyle tr:nth-child(even) {
            background: #E0E0E0;
        }

        .mystyle tr:hover {
            background: silver;
            cursor: pointer;
        }
        """
        html = f"""\
<html>
<head>{args.request} Playbook</head>
<style>
{css}
</style>
<body>
{html_table}
</body>
</html>
        """

        # 표준 출력으로 HTML 테이블을 출력합니다.
        print(html)
    except Exception as e:
        print("Error:" ,traceback.format_exc())
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    main()

