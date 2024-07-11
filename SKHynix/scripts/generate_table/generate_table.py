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
import os
parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
parser.add_argument("-f", "--file", type=str, nargs='+', help="read filenames example: -f filename1 filename2", required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
args= parser.parse_args()

# 사용자 홈 디렉토리 경로 얻기
home_dir = os.path.expanduser("~")
log_dir = os.path.join(home_dir, "logs")

# 로그 디렉토리가 존재하지 않으면 생성
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 로그 파일 경로 설정
log_file_path = os.path.join(log_dir, "generate_table.log")

# 로거 설정
logger = logging.getLogger('generate_table_log')
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
def read_json(filelist):
    data={}
    for json_file in filelist:
        with open(json_file, 'r') as file:
            data[json_file] = json.load(file)
    return data

def read_yaml(filelist):
    data={}
    for yaml_file in filelist:
        with open(yaml_file, 'r') as file:
            data[yaml_file] = yaml.load(file, Loader=yaml.FullLoader)
    return data

def storage_inode_report_by_cluster(data):
    tables=[]
    datatable = pandas.DataFrame()
    for cluster in data:
        try:
            inode_total=0
            inode_used=0
            for volume in cluster["ontap_info"]["storage/volumes"]["records"]:
                inode_total= inode_total+volume["files"]["maximum"]
                inode_used= inode_used+volume["files"]["used"]

            add=pandas.DataFrame.from_records([{
                'No': cluster["cluster"]["tier"],
                'Cluster name': cluster["cluster"]["name"],
                '업무 구분': cluster["cluster"]["description"],
                'INODE Total': inode_total,
                'INODE Used': inode_used,
                'INODE Free': inode_total - inode_used,
                'INODE Used Rate(%)': round(inode_used / inode_total * 100)
            }])
            datatable=datatable._append(add,ignore_index = True)
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"function: storage_inode_report_by_volume | KeyError: {e} - {cluster['cluster']['name']}",traceback.format_exc())
        except Exception as e:
            logger.error(f"function: storage_inode_report_by_volume | ",traceback.format_exc())
            print("function: storage_inode_report_by_volume | Error:" ,traceback.format_exc())
    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "CAD Storage Cluster INODE 사용량 Summary",
            'custom_col_styles': [
                'INODE Total', 
                'INODE Used', 
                'INODE Free'
            ],
            'sorting_rules': [
                {'column': 'No', 'order': 'asc'}
            ]
        }
    })
    return tables

def storage_inode_report_by_volume(data):
    tables=[]
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
                logger.error(f"function: storage_inode_report_by_volume | KeyError: {e} - {Cluster['cluster']['name']}/{Volume['name']}",traceback.format_exc())
            except Exception as e:
                logger.error(traceback.format_exc())
                print("function: storage_inode_report_by_volume | Error:" ,traceback.format_exc())

            datatable=datatable._append(add,ignore_index = True)
        tables.append({
            'datatable': datatable,
            'report_config': {
                'report_name': Cluster["cluster"]["name"] + " Storage Volumes INODE Report",
                'custom_col_styles': [
                    'INODE Total', 
                    'INODE Used', 
                    'INODE Free'
                ],
                'sorting_rules': [
                    {'column': 'INODE Used', 'order': 'desc'},
                    {'column': 'INODE Total', 'order': 'desc'}
                ]
            }
        })
    return tables

def storage_space_report_by_cluster(data):
    tables = []
    datatable = pandas.DataFrame()
    for cluster in data:
        total_size=0
        used_size=0
        try: 
            for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
                total_size= total_size+aggr["space"]["block_storage"]["size"]
                used_size= used_size+aggr["space"]["block_storage"]["used"]

            add=pandas.DataFrame.from_records([{
                'No': cluster["cluster"]["tier"],
                'Cluster name': cluster["cluster"]["name"],
                '업무 구분': cluster["cluster"]["description"],
                'Total Size(TB)': round(total_size/1024/1024/1024/1024),
                'Used Size(TB)': round(used_size/1024/1024/1024/1024),
                'Free Size(TB)': round((total_size - used_size)/1024/1024/1024/1024),
                'Used Rate(%)': round(used_size / total_size * 100)
            }])
            datatable=datatable._append(add,ignore_index = True)
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"function: storage_space_report_by_cluster | KeyError: {e} - {cluster['cluster']['name']}",traceback.format_exc())
        except Exception as e:
            logger.error(traceback.format_exc())
            print("function: storage_space_report_by_cluster | Error:" ,traceback.format_exc())
            
    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "CAD Storage Cluster Capacity Summary",
            'sorting_rules': [
                {'column': 'No', 'order': 'asc'}
            ]
        }
    })
    return tables

def storage_space_report_by_cluster(data):
    tables = []
    datatable = pandas.DataFrame()
    for cluster in data:
        total_size=0
        used_size=0
        try:
            for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
                total_size= total_size+aggr["space"]["block_storage"]["size"]
                used_size= used_size+aggr["space"]["block_storage"]["used"]

            add=pandas.DataFrame.from_records([{
                'No': cluster["cluster"]["tier"],
                'Cluster name': cluster["cluster"]["name"],
                '업무 구분': cluster["cluster"]["description"],
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
            logger.error(traceback.format_exc())
            print("Error:" ,traceback.format_exc())

    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "CAD Storage Cluster Capacity Summary",
            'sorting_rules': [
                {'column': 'No', 'order': 'asc'}
            ]
        }
    })
    return tables

def storage_space_report_by_aggr(data):
    tables = []
    datatable = pandas.DataFrame()
    for cluster in data:
        for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
            try:
                total_size=aggr["space"]["block_storage"]["size"]
                used_size=aggr["space"]["block_storage"]["used"]
                logical_used_size=aggr["space"]["efficiency_without_snapshots"]["logical_used"]
                ratio=round(logical_used_size/used_size,2)
                add=pandas.DataFrame.from_records([{
                    'No': cluster["cluster"]["tier"],
                    'Cluster Name': cluster["cluster"]["name"],
                    'Node Name': aggr["home_node"]["name"],
                    'Aggr Name': aggr["name"],
                    'Total Size(TB)': round(total_size/1024/1024/1024/1024,1),
                    'Used Size(TB)': round(used_size/1024/1024/1024/1024,1),
                    'Free Size(TB)': round((total_size - used_size)/1024/1024/1024/1024,1),
                    'Used Rate(%)': round(used_size / total_size * 100),
                    'logical_used_size(TB)': round(logical_used_size/1024/1024/1024/1024,1),
                    'Total_Logical_size(TB)': round((total_size*ratio)/1024/1024/1024/1024,1)
                }])
                datatable=datatable._append(add,ignore_index = True)
            except KeyError as e:
                # KeyError 발생시 처리 로직
                logger.error(f"KeyError: {e} - {cluster['cluster']['name']}/{aggr['name']}",traceback.format_exc())
            except Exception as e:
                logger.error(traceback.format_exc())
                print("Error:" ,traceback.format_exc())

    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "------ Aggregates Capacity Report ------",
            'sorting_rules':
            [
                {'column': 'No', 'order': 'asc'},
                {'column': 'Node Name', 'order': 'asc'}
            ]
        }
    })
    return tables

def storage_space_report_by_volume(data):
    tables = []
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
                logger.error(f"function: storage_space_report_by_volume | KeyError: {e} - {Volume['svm']['name']}/{Volume['name']}",traceback.format_exc())
            except Exception as e:
                logger.error(traceback.format_exc())
                print("function: storage_space_report_by_volume | Error:" ,traceback.format_exc())
                

        tables.append({
            'datatable': datatable,
            'report_config': {
                'report_name': cluster["cluster"]["name"] + " Storage Volumes Capacity Report",
                'sorting_rules': 
                [
                    {'column': 'Used Size(TB)', 'order': 'desc'}, 
                    {'column': 'Total Size(TB)', 'order': 'desc'}
                ]
            }
        })
    return tables
def storage_space_report_by_aggr_in_SoC(data):
    tables = []
    datatable = pandas.DataFrame()
    for cluster in data:
        for aggr in cluster["ontap_info"]["storage/aggregates"]["records"]:
            try:
                total_size=aggr["space"]["block_storage"]["size"]
                used_size=aggr["space"]["block_storage"]["used"]
                logical_used_size=aggr["space"]["efficiency_without_snapshots"]["logical_used"]
                ratio=round(aggr["space"]["efficiency_without_snapshots"]["ratio"],2)
                Aggr_tier = aggr["name"][:2]
                add=pandas.DataFrame.from_records([{
                    'Tier': Aggr_tier,
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
                logger.error(f"function: storage_space_report_by_aggr_in_SoC | KeyError: {e} - {cluster['cluster']['name']}/{aggr['name']}",traceback.format_exc())
            except Exception as e:
                logger.error(traceback.format_exc())
                print("function: storage_space_report_by_aggr_in_SoC | Error:" ,traceback.format_exc())

    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "------ Aggregates Capacity Report ------",
            'sorting_rules': 
            [
                {'column': 'No', 'order': 'asc'},
                {'column': 'Total Size(TB)', 'order': 'asc'}, 
                {'column': 'Node Name', 'order': 'desc'}
            ]
        }
    })
    return tables

def storage_space_report_by_volume_in_SoC(data):
    tables = []
    for cluster in data:
        datatable = pandas.DataFrame()
        for Volume in cluster["ontap_info"]["storage/volumes"]["records"]:
            try:
                total_size=Volume["space"]["size"] * (1 - Volume["space"]["snapshot"]["reserve_percent"]/100)
                used_size=Volume["space"]["used"]
                volume_logical_used=Volume["space"]["logical_space"]["used_by_afs"]
                Aggr_name = Volume["aggregates"][0]['name']
                Aggr_tier = Aggr_name[:2]
                if Volume["style"] == "flexgroup":
                    Aggr_name = "flexgroup"
                add=pandas.DataFrame.from_records([{
                    'Tier': Aggr_tier,
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
                logger.error(f"function: storage_space_report_by_volume_in_SoC | KeyError: {e} - {Volume['svm']['name']}/{Volume['name']}",traceback.format_exc())
            except Exception as e:
                logger.error(traceback.format_exc())
                print("function: storage_space_report_by_volume_in_SoC | Error:" ,traceback.format_exc())
                

        tables.append({
            'datatable': datatable,
            'report_config': {
                'report_name': "SoC" + cluster["cluster"]["name"] + " Storage Volumes Capacity Report",
                'sorting_rules': [
                    {'column': 'Used Size(TB)', 'order': 'desc'}, 
                    {'column': 'Total Size(TB)', 'order': 'desc'}
                ]
            }
        })
    return tables


def storage_snapmirror_report_by_cluster(data):
    tables = []
    datatable = pandas.DataFrame()
    for cluster in data:
        for snapmirror in cluster["ontap_info"]["snapmirror/relationships"]["records"]:
            try:
                unhealthy_reason = ""
                transfer_time = ""
                transfer_status = ""
                policy_name = ""
                if "unhealthy_reason" in snapmirror:
                    unhealthy_reason = snapmirror["unhealthy_reason"][0]["message"]
                
                if "transfer" in snapmirror:
                    transfer_time = snapmirror["transfer"]["end_time"]
                    transfer_status = snapmirror["transfer"]["state"]
                
                if "policy" in snapmirror:
                    if "name" in snapmirror["policy"]:
                        policy_name = snapmirror["policy"]["name"]
                    elif "uuid" in snapmirror["policy"]:
                        policy_name = snapmirror["policy"]["uuid"]

                add=pandas.DataFrame.from_records([{
                    'Cluster Name': cluster["cluster"]["name"],
                    'state': snapmirror["state"],
                    'healthy': snapmirror['healthy'],
                    'transfer end time': transfer_time,
                    'transfer status': transfer_status,
                    'policy': policy_name,
                    'unhealthy_reason': unhealthy_reason
                }])
                datatable=datatable._append(add,ignore_index = True)
            except KeyError as e:
                # KeyError 발생시 처리 로직
                logger.error(f"function: storage_snapmirror_report_by_cluster | KeyError: {e} - {cluster['cluster']['name']}/{snapmirror['uuid']}",traceback.format_exc())
            except Exception as e:
                logger.error(traceback.format_exc())
                print("function: storage_snapmirror_report_by_cluster | Error:" ,traceback.format_exc())

    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': f"{cluster['cluster']['name']} SnapVault Backup Daily Report"
            # 'sorting_rules': [
            #     {'column': 'transfer end time', 'order': 'asc'},
            #     {'column': 'healthy', 'order': 'asc'}
            # ]
        }
    })
    return tables


def storage_Big_snapshot_report_by_volume(data):
    tables = []
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
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"function: storage_Big_snapshot_report_by_volume | KeyError: {e} - {cluster['svm']['name']}/{volume['name']}",traceback.format_exc())
        except Exception as e:
            logger.error(f"function: storage_Big_snapshot_report_by_volume | ", traceback.format_exc())
            print("function: storage_Big_snapshot_report_by_volume | Error:" ,traceback.format_exc())
            

    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': data["cluster"]["name"] + " Storage Volumes Capacity Report-",
            'custom_col_styles': [
                'INODE Total', 
                'INODE Used', 
                'INODE Free'
            ],
            'sorting_rules': [
                {'column': 'Used Size(TB)', 'order': 'desc'}, 
                {'column': 'Total Size(TB)', 'order': 'desc'}
            ]
        }
    })
    return tables


def check_xcp_scan_status(data):
    tables = []
    datatable = pandas.DataFrame()
    for scaninfo in data:
        try:
            # scan_contents=scaninfo["ansible_facts"]["scan_contents"] * (1 - Volume["space"]["snapshot"]["reserve_percent"]/100)
            if "ansible_facts" not in scaninfo:
                status="PENDING"
                volumename = "None"
                xcp_info = "None"
            elif type(scaninfo["ansible_facts"]["status"]) != list:
                status="PENDING"
                volumename = "None"
                xcp_info = "None"
            else:    
                status=scaninfo["ansible_facts"]["status"][0]
                volumename = scaninfo["ansible_facts"]['volumename']
                xcp_info = scaninfo["scan_info_result"]['config']['xcp_info']

            add=pandas.DataFrame.from_records([{
                'status': status,
                'volumename': volumename,
                'xcp_run_info': xcp_info
            }])
            datatable=datatable._append(add,ignore_index = True)
        except KeyError as e:
            # KeyError 발생시 처리 로직
            logger.error(f"function: check_xcp_scan_status | KeyError : {e} - {scaninfo['config']['volumename']}",traceback.format_exc())
        except Exception as e:
            logger.error(traceback.format_exc())
            print("Error:" ,traceback.format_exc())
                
    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "check xcp scan status",
            'sorting_rules': [
                {'column': 'status', 'order': 'desc'}
            ]
        }
    })
    logger.debug(f"func : check_xcp_scan_status | datatable:")
    return tables

def get_sumdata_from_csv(filepath):
    total_file_size = 0
    file_count = 0
    with open(filepath, 'r') as file:
        for line in file:
            file_count += 1
            # 라인을 공백으로 분리
            items = line.split()
            # 첫 번째 항목을 정수로 변환하여 합계에 추가
            total_file_size += int(items[0])
    return total_file_size, file_count

def autopath_replace_status(data):
# autopath_result:
# - status: skip
#   message: 이미 수정된 파일이 존재합니다.
#   xcp_scan_status: PASSED
#   config:
#     xcp_result: /data/vine/Ansible_XCP/xcp_result/DRAM/20240701/result/wooyoung.result
#     xcp_info: /data/vine/Ansible_XCP/xcp_result/DRAM/20240701/info/wooyoung.info
#     replace: /data/vine/Ansible_XCP/xcp_result/DRAM/20240701/replace/wooyoung.replace
#     volumename: wooyoung
#     division: DRAM
#     automap: sim
#     searchdir: LAY SCH ESD CAE LDR CORE DV
    tables = []
    fail_table = pandas.DataFrame()
    ok_count = 0
    skip_count = 0
    fail_count = 0
    ignore_count = 0
    unknown_count = 0

    # autopath_result 리스트에서 모든 division을 수집하고 중복을 제거한다.
    # 예상 동작 divisions = [ DRAM, NAND, SOC ] 
    divisions = list({result['config']['division'] for result in data['autopath_result']})
    divisions_sum = {}
    for division in divisions:
        divisions_sum[division] = {'filesize': 0 , 'filecount': 0}

    for autopath_result in data['autopath_result']:
        if autopath_result['status'] == "skip":
            skip_count = skip_count +1
        elif autopath_result['status'] == "success":
            ok_count = ok_count + 1
        elif autopath_result['status'] == "ignore":
            ignore_count = ignore_count + 1
        elif autopath_result['status'] == "error":
            fail_count = fail_count + 1
        else:
            unknown_count = unknown_count + 1
    
        if autopath_result['config']['division'] in divisions:
            if autopath_result['status'] == "skip" or autopath_result['status'] == "success":
                division = autopath_result['config']['division']
                total_file_size, file_count = get_sumdata_from_csv(autopath_result['config']['replace'])
                divisions_sum[division] = {'filesize': divisions_sum[division].get('filesize', 0) + total_file_size, 'filecount': divisions_sum[division].get('filecount', 0) + file_count}
            else:
                add=pandas.DataFrame.from_records([{
                    'status': autopath_result['status'],
                    'volumename': autopath_result['config']['volumename'],
                    'xcp_run_info': autopath_result['config']['xcp_info']
                }])
                fail_table=fail_table._append(add,ignore_index = False)
        else:
            logger.error(f"func : autopath_replace_status | {autopath_result['config']['division']} not in divisions")


    # 출력 전 데이터 다듬기
    for division in divisions:
        divisions_sum[division] = {'file size(byte)': divisions_sum[division].get('filesize', 0) , 'file size(Gib)': round(divisions_sum[division].get('filesize', 0)/1024/1024/1024,2), 'file count': divisions_sum[division].get('filecount', 0)}
    
    datatable = pandas.DataFrame()
    # job report table
    add=pandas.DataFrame.from_records([{
        'ok_count': ok_count,
        'skip_count': skip_count,
        'ignore_count' : ignore_count,
        'fail_count': fail_count,
        'unknown_count': unknown_count
    }])
    datatable=datatable._append(add,ignore_index = False)

    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "autopath job report table",
            'index': True
        }
    })
    # data report table
    datatable=pandas.DataFrame.from_dict(divisions_sum, orient='index')
    logger.debug(f"func : autopath_replace_status | divisions_sum: {divisions_sum}")
    tables.append({
        'datatable': datatable,
        'report_config': {
            'report_name': "autopath data report table",
            'index': True
        },
        format : {
            'precision': 2,
            'thousands': ","
        },
    })
    logger.debug(f"func : autopath_replace_status | datatable:")

    # 실패한 작업 목록 후열 추가
    if not fail_table.empty:
        tables.append({
            'datatable': fail_table,
            'report_config': {
                'report_name': "autopath job fail list",
                'index': True
            }
        })
    return tables

def align_right():
    return 'text-align: right;'

def format_html_style(tables=[]):
    html_tables=[]
    for table in tables:
        # table = {
        #     'datatable': datatable,
        #     'report_config': {
        #         'report_name': "CAD Storage Cluster INODE 사용량 Summary",
        #         'index: True',
        #         'custom_col_styles': [
        #             'INODE Total', 
        #             'INODE Used', 
        #             'INODE Free'
        #         ],
        #         format : {
        #             'precision': 0,
        #             'thousands': ","
        #         },
        #         'sorting_rules': [
        #             {'column': 'tier', 'order': 'asc'}
        #         ]
        #     }
        # }
        logger.debug(f"func : format_html_style | table: {table}")
        datatable = table["datatable"]
        if "sorting_rules" in table["report_config"]:
            sort_columns = [rule['column'] for rule in table["report_config"]["sorting_rules"]]
            ascending_list = [rule['order'] == 'asc' for rule in table["report_config"]["sorting_rules"]]
            datatable = datatable.sort_values(by=sort_columns,ascending=ascending_list)
            # 정렬용 컬럼 'Sort_Age' 제거
            # datatable = datatable.drop('tier', axis=1)

        # 여기서 부터 스타일 객체로 변환됨
        datatable = datatable.style.set_caption(table["report_config"]["report_name"])
        # 튜플 값 표시 여부 
        if "index" in table["report_config"] and table["report_config"]["index"] == True:
            datatable = datatable.set_table_attributes('class="mystyle"')
        else:
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
        if "format" in table["report_config"]:
            datatable = datatable.format(precision=table["report_config"]["precision"], thousands=table["report_config"]["thousands"])
        else:
            datatable = datatable.format(precision=0, thousands=",")

        # custom_col_style_list에 있는 각 컬럼에 대해 오른쪽 정렬 스타일 적용
        if "custom_col_styles" in table["report_config"]:
            datatable = datatable.set_properties(subset=table["report_config"]["custom_col_styles"], **{'text-align': 'right'})

        html_tables.append(datatable.to_html())

    return html_tables

def main():
    try:
        if args.request == "clusters_inode_info":
            data=read_json(args.file)
            tables = storage_inode_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(tables)
        elif args.request == "volume_inode_info":
            data=read_json(args.file)
            tables = storage_inode_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(tables)
        elif args.request == "clusters_space_info":
            data=read_json(args.file)
            tables = storage_space_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(tables)
        elif args.request == "aggr_volume_space_info":
            data=read_json(args.file)
            tables = []
            aggr_tables = storage_space_report_by_aggr(data[args.file[0]]) 
            for table in aggr_tables:
                tables.append(table)
            volume_tables = storage_space_report_by_volume(data[args.file[1]])
            for table in volume_tables:
                tables.append(table)
            
            html_tables = format_html_style(tables)
        elif args.request == "aggrs_space_info":
            data=read_json(args.file)
            tables = storage_space_report_by_aggr(data[args.file[0]])
            html_tables = format_html_style(tables)
        elif args.request == "volume_space_info":
            data=read_json(args.file)
            tables = storage_space_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(tables)
        elif args.request == "big_snapshot_info":
            data=read_json(args.file)
            tables = storage_Big_snapshot_report_by_volume(data[args.file[0]])
            html_tables = format_html_style(tables)
        elif args.request == "aggr_volume_space_info_in_soc":
            data=read_json(args.file)
            tables = []
            aggr_tables = storage_space_report_by_aggr_in_SoC(data[args.file[0]]) 
            for table in aggr_tables:
                tables.append(table)
            volume_tables = storage_space_report_by_volume_in_SoC(data[args.file[1]])
            for table in volume_tables:
                tables.append(table)
            html_tables = format_html_style(tables)
        elif args.request == "clusters_snapmirror_info":
            data=read_json(args.file)
            tables = storage_snapmirror_report_by_cluster(data[args.file[0]])
            html_tables = format_html_style(tables)
        
        elif args.request == "check_xcp_scan_status":
            data=read_json(args.file)
            tables = check_xcp_scan_status(data[args.file[0]])
            html_tables = format_html_style(tables)

        elif args.request == "autopath_replace_status":
            data=read_yaml(args.file)
            tables = autopath_replace_status(data[args.file[0]])
            html_tables = format_html_style(tables)

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
        logger.info("print success the HTML")
    except Exception as e:
        print("Error:" ,traceback.format_exc())
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    main()




