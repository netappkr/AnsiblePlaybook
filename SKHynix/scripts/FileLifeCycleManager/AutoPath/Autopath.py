import re
import os
import argparse
import yaml
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

def modify_lines(data_lines, replacement_dict):
    modified_lines = []
    for line in data_lines:
        modified_line = line
        for key, value in replacement_dict.items():
            if key in line:
                modified_line = line.replace(key, f"/{value}/{key.split('/')[-1]}")
                break
        modified_lines.append(modified_line)
    return modified_lines

def read_yaml_config(config_file_path):
    with open(config_file_path, 'r', encoding='utf-8') as config_file:
        return yaml.safe_load(config_file)

def main(data_file_path, auto_sim_file_path, searchdirs):
    try:
        replacement_dict = read_auto_sim(auto_sim_file_path)
        data_lines = read_data_file(data_file_path)
        modified_lines = modify_lines(data_lines, replacement_dict)
        # config = read_yaml_config(config_file_path)
        result= []
        # 필요한 데이터만 출력
        logger.debug(f"function: main | searchdirs: {searchdirs}, autopath: {auto_sim_file_path}, datafile: {data_file_path}")
        if searchdirs is not None:
            for line in modified_lines:
                if re.match(r'^\d+ \S+/\S+', line) and any(searchdir in line for searchdir in searchdirs):
                    result.append(line)
                    print(line, end='')
                    logger.debug(f"function: main | filter message : {line}")
        else:
            for line in modified_lines:
                if re.match(r'^\d+ \S+/\S+', line):
                    result.append(line)
                    print(line, end='')
                    logger.debug(f"function: main | message : {line}")


        # 결과를 파일로 저장하려면 아래 코드 사용
        output_file_path = f"{data_file_path}.auto"
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            for line in result:
                output_file.write(line)
        logger.info(f"{output_file_path}: 파일 출력 설공 ")
    except Exception as e:
        logger.error(traceback.format_exc())
        print("Error:" ,traceback.format_exc())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the data file")
    parser.add_argument("-a", "--auto", type=str, required=True, help="Path to the auto.sim file")
    # parser.add_argument("--config", type=str, required=False, help="Path to the config YAML file")
    parser.add_argument("--searchdir", type=str, nargs='+', required=True, help="List of search directories")
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
    logger.setLevel(logging.DEBUG)  # 로그 레벨 설정

    # 로그 포맷 설정
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 파일 핸들러 설정
    file_handler = logging.FileHandler(log_file_path, mode='a')  # 파일 경로를 정확하게 지정
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # main(args.file, args.auto, args.config, args.searchdir)
    main(args.file, args.auto, args.searchdir)

    
