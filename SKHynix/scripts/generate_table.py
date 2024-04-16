#!/usr/bin/env python3
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
args= parser.parse_args()
report_names=[]
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
data={}
for json_file in args.file:
    with open(json_file, 'r') as file:
        data[json_file] = json.load(file)
# Pandas DataFrame을 생성합니다.
datatables = []

def format_with_commas(num):
    return '{0:,}'.format(num)

def storage_inode_report_by_cluster(data):
    global datatables
    report_names = []
    datatable = pandas.DataFrame()
    for cluster in data:
        inode_total=0
        inode_used=0
        for volume in cluster["ontap_info"]["storage/volumes"]["records"]:
            inode_total= inode_total+volume["files"]["maximum"]
            inode_used= inode_used+volume["files"]["used"]

        add=pandas.DataFrame.from_records([{
            'Cluster name': cluster["cluster"]["name"],
            '업무 구분': cluster["cluster"]["description"],
            'INODE Total': format_with_commas(inode_total),
            'INODE Used': format_with_commas(inode_used),
            'INODE Free': format_with_commas(inode_total - inode_used),
            'INODE Used Rate(%)': round(inode_used / inode_total * 100)
        }])
        datatable=datatable._append(add,ignore_index = True)
    datatables.append(datatable)
    custom_col_style_list=['Total Inodes','Used Inodes','Free Inodes']
    report_names.append("CAD Storage Cluster INODE 사용량 Summary")
    return report_names, custom_col_style_list

def storage_inode_report_by_volume(data):
    global datatables
    report_names = []
    for Cluster in data:
        datatable = pandas.DataFrame()
        for Volume in Cluster["ontap_info"]["storage/volumes"]["records"]:
            Aggr_name = Volume["aggregates"][0]['name']
            if Volume["style"] == "flexgroup":
                Aggr_name = "-"
            add=pandas.DataFrame.from_records([{
                'cluster Name': Cluster["cluster"]["name"],
                'SVM Name': Volume["svm"]["name"],
                'Aggregate': Aggr_name,
                'type': Volume["style"],
                'Volume': Volume["name"],
                'INODE Total': format_with_commas(Volume["files"]["maximum"]),
                'INODE Used': format_with_commas(Volume["files"]["used"]),
                'INODE Free': format_with_commas(Volume["files"]["maximum"] - Volume["files"]["used"]),
                'INode Used Rate(%)': round(Volume["files"]["used"] / Volume["files"]["maximum"] * 100)
            }])

            datatable=datatable._append(add,ignore_index = True)
        datatables.append(datatable)
        report_names.append(Cluster["cluster"]["name"] + "Storage Volumes INODE Report")
    custom_col_style_list=['Total Inodes','Used Inodes','Free Inodes']
    return report_names, custom_col_style_list

def storage_space_report_by_cluster(data):
    global datatables
    report_names = []
    datatable = pandas.DataFrame()
    for cluster in data:
        total_size=0
        used_size=0
        for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
            total_size= total_size+aggr["space"]["block_storage"]["size"]
            used_size= used_size+aggr["space"]["block_storage"]["used"]

        add=pandas.DataFrame.from_records([{
            'Cluster name': cluster["cluster"]["name"],
            '업무 구분': cluster["cluster"]["description"],
            'Total Size(TB)': format_with_commas(round(total_size/1024/1024/1024/1024)),
            'Used Size(TB)': format_with_commas(round(used_size/1024/1024/1024/1024)),
            'Free Size(TB)': format_with_commas(round((total_size - used_size)/1024/1024/1024/1024)),
            'Used Rate(%)': round(used_size / total_size * 100)
        }])
        datatable=datatable._append(add,ignore_index = True)
    datatables.append(datatable)
    report_names.append("CAD Storage Cluster 사용량 Summary")
    return report_names

def storage_space_report_by_aggr(data):
    global datatables
    report_names = []
    datatable = pandas.DataFrame()
    for cluster in data:
        for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
            total_size=aggr["space"]["block_storage"]["size"]
            used_size=aggr["space"]["block_storage"]["used"]

            add=pandas.DataFrame.from_records([{
                'Cluster Name': cluster["cluster"]["name"],
                'Node Name': aggr["home_node"]["name"],
                'Aggr Name': aggr["name"],
                'Total Size(TB)': format_with_commas(round(total_size/1024/1024/1024/1024,1)),
                'Used Size(TB)': format_with_commas(round(used_size/1024/1024/1024/1024,1)),
                'Free Size(TB)': format_with_commas(round((total_size - used_size)/1024/1024/1024/1024,1)),
                'Used Rate(%)': round(used_size / total_size * 100)
            }])
            datatable=datatable._append(add,ignore_index = True)
    datatables.append(datatable)
    report_names.append("------ Aggregates Capacity Report ------")
    return report_names

def storage_space_report_by_volume(data):
    global datatables
    report_names = []
    for cluster in data:
        datatable = pandas.DataFrame()
        for Volume in cluster["ontap_info"]["storage/volumes"]["records"]:
            total_size=Volume["space"]["size"] * (1 - Volume["space"]["snapshot"]["reserve_percent"]/100)
            used_size=Volume["space"]["used"]
            
            Aggr_name = Volume["aggregates"][0]['name']
            if Volume["style"] == "flexgroup":
                Aggr_name = "-"
            add=pandas.DataFrame.from_records([{
                'SVM Name': Volume["svm"]["name"],
                'Aggregate': Aggr_name,
                'Total Size(TB)': format_with_commas(round(total_size/1024/1024/1024)),
                'Used Size(TB)': format_with_commas(round(used_size/1024/1024/1024)),
                'Free Size(TB)': format_with_commas(round((total_size - used_size)/1024/1024/1024)),
                'Used Rate(%)': round(used_size / total_size * 100)
            }])
            datatable=datatable._append(add,ignore_index = True)
        datatables.append(datatable)
        report_names.append(cluster["cluster"]["name"] + " Storage Volumes Capacity Report-")
    return report_names

def storage_Big_snapshot_report_by_volume(data):
    global datatables
    report_names = []
    datatable = pandas.DataFrame()
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
                        'Total Size(GiB)': round(total_size/1024/1024/1024,2),
                        'Used Size(GiB)': round(used_size/1024/1024/1024,2),
                        'Free Size(GiB)': round((total_size - used_size)/1024/1024/1024,2),
                        'Used Rate(%)': round(used_size / total_size,2),
                        'snaphost Used(Tib)': round(snapshot_used/1024/1024/1024/1024,2)
                    }])
                    datatable = datatable._append(add,ignore_index = True)
        datatables.append(datatable)
    report_names.append(data["cluster"]["name"] + " Storage Volumes Capacity Report-")
    return report_names

def align_right():
    return 'text-align: right;'

def format_html_style(datatables, report_names, custom_col_style_list=[]):
    html_tables=[]
    for datatable in datatables:
        for report_name in report_names:
            report_name = report_name
        datatable = datatable.style.set_caption(report_name).set_table_attributes('class="mystyle"').hide()
    
        # custom_col_style_list에 있는 각 컬럼에 대해 오른쪽 정렬 스타일 적용
        for col in custom_col_style_list:
            datatable = datatable.applymap(align_right, subset=[col])
        
        html_tables.append(datatable.to_html())
    return html_tables

def main():
    try:
        if args.request == "clusters_inode_info":
            report_names, custom_col_style_list = storage_inode_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "volume_inode_info":
            report_names, custom_col_style_list = storage_inode_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "clusters_space_info":
            report_names=storage_space_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "aggr_volume_space_info":
            report_names=[]
            # datatable은 실행순서 대로 list에 추가됨 
            # report name을 실행 순서대로 list에 추가함 
            # datatable도 전역 변수 쓰지말고 돌릴까 고민중 
            for report_name in storage_space_report_by_aggr(data[args.file[0]]):
                report_names.append(report_name)
            for report_name in storage_space_report_by_volume(data[args.file[1]]):
                report_names.append(report_name)
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "aggrs_space_info":
            report_names=storage_space_report_by_aggr(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "volume_space_info":
            report_names=storage_space_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "big_snapshot_info":
            report_names=storage_Big_snapshot_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        else:
            logger.error(args.request+" request is not matched")
            html_tables = [args.request+" request is not matched"]
             
        # HTML 테이블로 변환합니다.
        ## 경고
        # Html 양식의 이메일 제출 시 CSS 포함 전송기능을 지원하지 않는 경우가 대부분이라고 합니다.
        # 따라서 방법은 각 Html 항목에 직접 css를 한줄씩 넣어야 합니다.
        css = """
        .mystyle {
            font-size: 11pt; 
            font-family: Arial;
            border-collapse: collapse; 
            border: 1px solid black;
        }

        .mystyle td, th {
            padding: 5px;
            text-align: center;
	        border: 1px solid black;
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
{'<br></br><br></br>'.join(html_tables)}
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

