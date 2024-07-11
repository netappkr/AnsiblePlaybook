#!/usr/bin/env python3
import re
import os
import argparse
import yaml
import json
import logging
import traceback

def read_auto_sim(auto_sim_file_path):
    replacement_dict = {}
    with open(auto_sim_file_path, 'r', encoding='utf-8') as auto_sim_file:
        for line in auto_sim_file:
            parts = line.split()
            if len(parts) == 2:
                key = parts[1]
                value = parts[0]
                replacement_dict[key] = value
    return replacement_dict

def read_data_file(data_file_path):
    with open(data_file_path, 'r', encoding='utf-8') as data_file:
        return data_file.readlines()

def modify_lines(data_lines, replacement_dict, automap):
# nsimtc.chopincad.com:/sim_nand_ptissptv/CAE/USER -> /sim/ptissptv/CAE/USER
#
    modified_lines = []
    file_count = 0
    for line in data_lines:
        modified_line = line
        for key, value in replacement_dict.items():
            # logger.debug(f"function: modify_lines | key : {key}, value : {value}")
            if key in line:
                modified_line = line.replace(key, f"/{automap}/{value}")
                logger.debug(f"function: modify_lines | modified_line : {modified_line}")
                break
        modified_lines.append(modified_line)
    return modified_lines

def read_yaml_config(config_file_path):
    with open(config_file_path, 'r', encoding='utf-8') as config_file:
        return yaml.safe_load(config_file)

def result_data(jobstatus,message,xcpinfo,xcpresult,replace):
    result = {
        "status": jobstatus,
        "message": message,
        "xcp_info":xcpinfo,
        "xcp_result": xcpresult,
        "replace": replace
    }
    return result

def main(xcpresult, xcpinfo, replace, automap, searchdirs, volumename, status, skipdedup):
    try:
        message = ""
        jobstatus = ""
        if os.path.isfile(replace) and (skipdedup == "on"):
            message = "이미 수정된 파일이 존재합니다."
            jobstatus = "skip"
            logger.info(result_data(jobstatus,message,xcpinfo,xcpresult,replace))
            return result_data(jobstatus,message,xcpinfo,xcpresult,replace)

        if status == "PASSED":
            replacement_dict = read_auto_sim(f"/tmp/auto.{automap}")
            data_lines = read_data_file(xcpresult)
            modified_lines = modify_lines(data_lines, replacement_dict, automap)
            # config = read_yaml_config(config_file_path)
            result= []
            # 필요한 데이터만 출력
            logger.debug(f"function: main | searchdirs: {searchdirs}, autopath: /tmp/auto.{automap}, datafile: {xcpresult}, status: {status}")
            if searchdirs is not None:
                for line in modified_lines:
                    logger.debug(f"function: main | filter volumename : {volumename}")
                    if re.match(r'^\d+ \S+/\S+', line) and any(searchdir in line for searchdir in searchdirs):
                        result.append(line)
                        # print(line, end='')
                        logger.debug(f"function: main | filter message : {line}")

            else:
                for line in modified_lines:
                    if re.match(r'^\d+ \S+/\S+', line):
                        result.append(line)
                        # print(line, end='')
                        logger.debug(f"function: main | message : {line}")


            # 결과를 파일로 저장하려면 아래 코드 사용
            with open(replace, 'w', encoding='utf-8') as output_file:
                for line in result:
                    output_file.write(line)
            message = "파일 수정 성공"
            jobstatus = "success"
            logger.info(result_data(jobstatus,message,xcpinfo,xcpresult,replace))
            return result_data(jobstatus,message,xcpinfo,xcpresult,replace)
        else:
            message = f"{volumename} 볼륨의 XCP scan 상태는 {status} 입니다. PASSED가 아니면 작업을 생략합니다."
            jobstatus = "ignore"
            logger.info(result_data(jobstatus,message,xcpinfo,xcpresult,replace))
            return result_data(jobstatus,message,xcpinfo,xcpresult,replace)
        
    except Exception as e:
        message = traceback.format_exc()
        jobstatus = "error"
        logger.error(result_data(jobstatus,message,xcpinfo,xcpresult,replace))
        return result_data(jobstatus,message,xcpinfo,xcpresult,replace)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
    parser.add_argument("--xcpresult", type=str, required=True, help="Path to the xcp_result data file")
    parser.add_argument("--xcpinfo", type=str, required=True, help="Path to the xcp_info data file")
    parser.add_argument("--replace", type=str, required=True, help="Path to the replace file")
    parser.add_argument("--automap", type=str, required=True, help="automap valuse")
    # parser.add_argument("--config", type=str, required=False, help="Path to the config YAML file")
    parser.add_argument("--searchdir", type=str, nargs='+', required=True, help="List of search directories")
    parser.add_argument("--volumename", type=str, required=True, help="volumename valuse")
    parser.add_argument("--status", type=str, required=True, help="xcp scan status")
    parser.add_argument("--skipdedup", type=str, required=False, default="off", help="skip duplicate job.")
    args = parser.parse_args()
    # 사용자 홈 디렉토리 경로 얻기
    home_dir = os.path.expanduser("~")
    log_dir = os.path.join(home_dir, "logs")

    # 로그 디렉토리가 존재하지 않으면 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로그 파일 경로 설정
    log_file_path = os.path.join(log_dir, "autopath.log")

    # 로거 설정
    logger = logging.getLogger('autopath')
    logger.setLevel(logging.INFO)  # 로그 레벨 설정

    # 로그 포맷 설정
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 파일 핸들러 설정
    file_handler = logging.FileHandler(log_file_path, mode='a')  # 파일 경로를 정확하게 지정
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # main(args.file, args.auto, args.config, args.searchdir)
    result = main(args.xcpresult, args.xcpinfo, args.replace, args.automap, args.searchdir, args.volumename, args.status, args.skipdedup)
    print(json.dumps(result,ensure_ascii=False))

