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
# logger
logger = logging.getLogger(name='generate_table_log')
logger.setLevel(logging.DEBUG) ## 경고 수준 설정
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

# def format_with_commas(num):
#     return '{0:,}'.format(num)

def storage_inode_report_by_cluster(data):
    global datatables
    report_names = []
    sorted_dict = {}
    custom_col_style_list = []
    datatable = pandas.DataFrame()
    for cluster in data:
        try:
            inode_total=0
            inode_used=0
            for volume in cluster["ontap_info"]["storage/volumes"]["records"]:
                inode_total= inode_total+volume["files"]["maximum"]
                inode_used= inode_used+volume["files"]["used"]

            add=pandas.DataFrame.from_records([{
                'Cluster name': cluster["cluster"]["name"],
                '업무 구분': cluster["cluster"]["description"],
                'tier': cluster["cluster"]["tier"],
                'INODE Total': inode_total,
                'INODE Used': inode_used,
                'INODE Free': inode_total - inode_used,
                'INODE Used Rate(%)': round(inode_used / inode_total * 100)
            }])
            datatable=datatable._append(add,ignore_index = True)
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"KeyError: {e} - {cluster['cluster']['name']}",traceback.format_exc())
        except Exception as e:
            print("Error:" ,traceback.format_exc())
            logger.error(traceback.format_exc())
    datatables.append(datatable)
    custom_col_style_list.append(['INODE Total','INODE Used','INODE Free'])
    sorted_dict.update([
        {
            'column': 'tier', 
            'order': 'asc'
        }
    ])
    report_names.append("CAD Storage Cluster INODE 사용량 Summary")
    return report_names, custom_col_style_list, sorted_dict

def storage_inode_report_by_volume(data):
    global datatables
    report_names = []
    sorted_dict = {}
    custom_col_style_list = []
    for Cluster in data:
        datatable = pandas.DataFrame()
        for Volume in Cluster["ontap_info"]["storage/volumes"]["records"]:
            try: 
                Aggr_name = Volume["aggregates"][0]['name']
                if Volume["style"] == "flexgroup":
                    Aggr_name = "-"
                add=pandas.DataFrame.from_records([{
                    'cluster Name': Cluster["cluster"]["name"],
                    'SVM Name': Volume["svm"]["name"],
                    'Aggregate': Aggr_name,
                    'type': Volume["style"],
                    'Volume': Volume["name"],
                    'INODE Total': Volume["files"]["maximum"],
                    'INODE Used': Volume["files"]["used"],
                    'INODE Free': Volume["files"]["maximum"] - Volume["files"]["used"],
                    'INode Used Rate(%)': round(Volume["files"]["used"] / Volume["files"]["maximum"] * 100)
                }])
            except KeyError as e:
                # KeyError 발생시 처리 로직
                logger.error(f"KeyError: {e} - {Cluster['cluster']['name']}/{Volume['name']}",traceback.format_exc())
            except Exception as e:
                print("Error:" ,traceback.format_exc())
                logger.error(traceback.format_exc())

            datatable=datatable._append(add,ignore_index = True)
        datatables.append(datatable)
        report_names.append(Cluster["cluster"]["name"] + " Storage Volumes INODE Report")
        custom_col_style_list.append(['INODE Total','INODE Used','INODE Free'])
        sorted_dict.update([
            {
                'column': 'INODE Used', 
                'order': 'desc'
            }, 
            {
                'column': 'INODE Total', 
                'order': 'desc'
            }
        ])
    return report_names, custom_col_style_list, sorted_dict

def storage_space_report_by_cluster(data):
    global datatables
    report_names = []
    sorted_dict = {}
    custom_col_style_list = []
    datatable = pandas.DataFrame()
    for cluster in data:
        total_size=0
        used_size=0
        try: 
            for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
                total_size= total_size+aggr["space"]["block_storage"]["size"]
                used_size= used_size+aggr["space"]["block_storage"]["used"]

            add=pandas.DataFrame.from_records([{
                'Cluster name': cluster["cluster"]["name"],
                '업무 구분': cluster["cluster"]["description"],
                'tier': cluster["cluster"]["tier"],
                'Total Size(TB)': round(total_size/1024/1024/1024/1024),
                'Used Size(TB)': round(used_size/1024/1024/1024/1024),
                'Free Size(TB)': round((total_size - used_size)/1024/1024/1024/1024),
                'Used Rate(%)': round(used_size / total_size * 100)
            }])
            datatable=datatable._append(add,ignore_index = True)
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"KeyError: {e} - {cluster['cluster']['name']}",traceback.format_exc())
        except Exception as e:
            print("Error:" ,traceback.format_exc())
            logger.error(traceback.format_exc())
    datatables.append(datatable)
    custom_col_style_list.append(["None"])
    sorted_dict.update([
        {
            'column': 'tier', 
            'order': 'asc'
        },
        {
            'column': 'Used Size(TB)', 
            'order': 'desc'
        }, 
        {
            'column': 'Total Size(TB)', 
            'order': 'desc'
        }
    ])
    report_names.append("CAD Storage Cluster 사용량 Summary")
    return report_names, custom_col_style_list, sorted_dict

def storage_space_report_by_aggr(data):
    global datatables
    report_names = []
    sorted_dict = {}
    custom_col_style_list = []
    datatable = pandas.DataFrame()
    for cluster in data:
        for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
            try:
                total_size=aggr["space"]["block_storage"]["size"]
                used_size=aggr["space"]["block_storage"]["used"]
                logical_used_size=aggr["space"]["efficiency_without_snapshots"]["logical_used"]
                ratio=round(aggr["space"]["efficiency_without_snapshots"]["ratio"],2)
                add=pandas.DataFrame.from_records([{
                    'tier': cluster["cluster"]["tier"],
                    'Cluster Name': cluster["cluster"]["name"],
                    'Node Name': aggr["home_node"]["name"],
                    'Aggr Name': aggr["name"],
                    'Total Size(TB)': round(total_size/1024/1024/1024/1024,1),
                    'Used Size(TB)': round(used_size/1024/1024/1024/1024,1),
                    'Free Size(TB)': round((total_size - used_size)/1024/1024/1024/1024,1),
                    'Used Rate(%)': round(used_size / total_size * 100),
                    'logical_used_size(TB)': round(logical_used_size/1024/1024/1024/1024,1),
                    'Total_Logical_size(TB)': round((logical_used_size*ratio)/1024/1024/1024/1024,1)
                }])
                datatable=datatable._append(add,ignore_index = True)
            except KeyError as e:
                # KeyError 발생시 처리 로직
                logger.error(f"KeyError: {e} - {cluster['cluster']['name']}/{aggr['name']}",traceback.format_exc())
            except Exception as e:
                print("Error:" ,traceback.format_exc())
                logger.error(traceback.format_exc())

    datatables.append(datatable)
    custom_col_style_list.append(["None"])
    sorted_dict.update([
        {
            'column': 'tier', 
            'order': 'asc'
        },
        {
            'column': 'Total Size(TB)', 
            'order': 'asc'
        }, 
        {
            'column': 'Node Name', 
            'order': 'desc'
        }
    ])
    report_names.append("------ Aggregates Capacity Report ------")
    return report_names, custom_col_style_list, sorted_dict

def storage_space_report_by_volume(data):
    global datatables
    report_names = []
    sorted_dict = {}
    custom_col_style_list = []
    for cluster in data:
        datatable = pandas.DataFrame()
        for Volume in cluster["ontap_info"]["storage/volumes"]["records"]:
            try:
                total_size=Volume["space"]["size"] * (1 - Volume["space"]["snapshot"]["reserve_percent"]/100)
                used_size=Volume["space"]["used"]
                volume_logical_used=Volume["space"]["logical_space"]["used_by_afs"]
                Aggr_name = Volume["aggregates"][0]['name']
                if Volume["style"] == "flexgroup":
                    Aggr_name = "-"
                add=pandas.DataFrame.from_records([{
                    'SVM Name': Volume["svm"]["name"],
                    'Aggregate': Aggr_name,
                    'Volume': Volume['name'],
                    'Total Size(TB)': round(total_size/1024/1024/1024),
                    'Used Size(TB)': round(used_size/1024/1024/1024),
                    'Free Size(TB)': round((total_size - used_size)/1024/1024/1024),
                    'Used Rate(%)': round(used_size / total_size * 100),
                    'Logical Used Size(TB)': round(volume_logical_used/1024/1024/1024)
                }])
                datatable=datatable._append(add,ignore_index = True)
            except KeyError as e:
                # KeyError 발생시 처리 로직
                logger.error(f"KeyError: {e} - {Volume['svm']['name']}/{Volume['name']}",traceback.format_exc())
            except Exception as e:
                print("Error:" ,traceback.format_exc())
                logger.error(traceback.format_exc())

        datatables.append(datatable)
        custom_col_style_list.append(["None"])
        sorted_dict.update([
            {
                'column': 'Used Size(TB)', 
                'order': 'desc'
            }, 
            {
                'column': 'Total Size(TB)', 
                'order': 'desc'
            }
        ])
        report_names.append(cluster["cluster"]["name"] + " Storage Volumes Capacity Report")
    return report_names, custom_col_style_list, sorted_dict

def storage_Big_snapshot_report_by_volume(data):
    global datatables
    report_names = []
    sorted_dict = {}
    custom_col_style_list = []
    datatable = pandas.DataFrame()
    for cluster in data:
        try:
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
            custom_col_style_list.append(["None"])
            sorted_dict.update([
                {
                    'column': 'Used Size(TB)', 
                    'order': 'desc'
                }, 
                {
                    'column': 'Total Size(TB)', 
                    'order': 'desc'
                }
            ])
            report_names.append(data["cluster"]["name"] + " Storage Volumes Capacity Report-")
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"KeyError: {e} - {cluster['svm']['name']}/{volume['name']}",traceback.format_exc())
        except Exception as e:
            print("Error:" ,traceback.format_exc())
            logger.error(traceback.format_exc())
    return report_names, custom_col_style_list, sorted_dict

def align_right():
    return 'text-align: right;'

def format_html_style(datatables, report_names, custom_col_style_lists=[],sorted_dicts=[]):
    html_tables=[]
    for report_name, datatable, custom_col_style_list, sorted_dict in zip(report_names, datatables, custom_col_style_lists, sorted_dicts):
        # .sort_values()
        if sorted_dict != {}:
            sort_columns = [rule['column'] for rule in sorted_dict]
            ascending_list = [rule['order'] == 'asc' for rule in sorted_dict]
            datatable = datatable.sort_values(by=sort_columns,ascending=ascending_list)
            # 정렬용 컬럼 'Sort_Age' 제거
            # datatable = datatable.drop('tier', axis=1)

        # 여기서 부터 스타일 객체로 변환됨
        datatable = datatable.style.set_caption(report_name)
        datatable = datatable.set_table_attributes('class="mystyle"').hide()
        # Css 클래스를 정의 해서 사용하기로함
        # styles = [
        #     {"selector": ".mystyle", "props": [("font-size", "11pt"), 
        #                                     ("font-family", "Arial"), 
        #                                     ("border-collapse", "collapse"), 
        #                                     ("border", "1px solid black")]},
        #     {"selector": ".mystyle td, .mystyle th", "props": [("padding", "5px"), 
        #                                                     ("text-align", "center"), 
        #                                                     ("border", "1px solid black")]},
        #     {"selector": ".mystyle caption", "props": [("font-size", "16pt")]},
        #     {"selector": ".mystyle tr:nth-child(even)", "props": [("background", "#E0E0E0")]},
        #     {"selector": ".mystyle tr:hover", "props": [("background", "silver"), 
        #                                                 ("cursor", "pointer")]}
        # ]
        # datatable = datatable.set_table_styles(styles)
        # datatable = datatable.format('{:,.0f}', subset=custom_col_style_list)
        datatable = datatable.format(precision=0, thousands=",")

        # custom_col_style_list에 있는 각 컬럼에 대해 오른쪽 정렬 스타일 적용
        if custom_col_style_list != ["None"]:
            datatable = datatable.set_properties(subset=custom_col_style_list, **{'text-align': 'right'})

        html_tables.append(datatable.to_html())
    return html_tables

def main():
    try:
        if args.request == "clusters_inode_info":
            report_names, custom_col_style_list, sorted_dict = storage_inode_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names,custom_col_style_list,sorted_dict)
        elif args.request == "volume_inode_info":
            report_names, custom_col_style_list, sorted_dict = storage_inode_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names,custom_col_style_list,sorted_dict)
        elif args.request == "clusters_space_info":
            report_names, custom_col_style_list, sorted_dict = storage_space_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names,custom_col_style_list,sorted_dict)
        elif args.request == "aggr_volume_space_info":
            report_names=[]
            sorted_dicts=[]
            custom_col_style_lists=[]
            # datatable은 실행순서대로 list에 추가됨
            report_name, custom_col_style_list, sorted_dict = storage_space_report_by_aggr(data[args.file[0]]) 
            for report_name, custom_col_style_list, sorted_dict in zip(report_name, custom_col_style_list, sorted_dict):
                report_names.append(report_name)
                custom_col_style_lists.append(custom_col_style_list)
                sorted_dicts.append(sorted_dict)
            report_name, custom_col_style_list, sorted_dict = storage_space_report_by_volume(data[args.file[1]])
            for report_name, custom_col_style_list, sorted_dict in zip(report_name, custom_col_style_list, sorted_dict):
                report_names.append(report_name)
                custom_col_style_lists.append(custom_col_style_list)
                sorted_dicts.append(sorted_dict)
            
            html_tables = format_html_style(datatables,report_names,custom_col_style_lists,sorted_dicts)
        elif args.request == "aggrs_space_info":
            report_name, custom_col_style_list, sorted_dict = storage_space_report_by_aggr(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "volume_space_info":
            report_name, custom_col_style_list, sorted_dict = storage_space_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(datatables,report_names)
        elif args.request == "big_snapshot_info":
            report_name, custom_col_style_list, sorted_dict = storage_Big_snapshot_report_by_volume(data[args.file[0]])
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


