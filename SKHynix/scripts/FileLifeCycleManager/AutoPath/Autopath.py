import re
import os
import argparse
import yaml

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

def main(data_file_path, auto_sim_file_path, config_file_path, searchdirs):
    replacement_dict = read_auto_sim(auto_sim_file_path)
    data_lines = read_data_file(data_file_path)
    modified_lines = modify_lines(data_lines, replacement_dict)
    # config = read_yaml_config(config_file_path)
    
    # 필요한 데이터만 출력
    for line in modified_lines:
        if re.match(r'^\d+ \S+/\S+', line) and any(searchdir in line for searchdir in searchdirs):
            print(line, end='')

    # 결과를 파일로 저장하려면 아래 코드 사용
    output_file_path = 'outputfile.txt'
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        for line in modified_lines:
            if re.match(r'^\d+ \S+/\S+', line) and any(searchdir in line for searchdir in searchdirs):
                output_file.write(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the data file")
    parser.add_argument("-a", "--auto", type=str, required=True, help="Path to the auto.sim file")
    parser.add_argument("--config", type=str, required=False, help="Path to the config YAML file")
    parser.add_argument("--searchdir", type=str, nargs='+', required=True, help="List of search directories")
    args = parser.parse_args()

    main(args.file, args.auto, args.config, args.searchdir)

    
