import re
import argparse
parser = argparse.ArgumentParser(description="Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts")
parser.add_argument("-f", "--file", type=str, nargs='+', help="read filenames example: -f filename1 filename2", required=False)
parser.add_argument("-r", "--request", type=str, help="request type",required=False)
parser.add_argument("--config", type=str, help="config.yaml",required=True)
args= parser.parse_args()

# 데이터 파일과 변경할 데이터를 찾을 파일 경로 설정
data_file_path = 'path/to/datafile.txt'
auto_sim_file_path = 'path/to/auto.sim'
config_file = args.config
# scan_info:
# - volumename: data 
#   result: /data/vine/Ansible_XCP
#   division: DRAM
#   automap: sim
#   searchdir: [test]

# auto.sim 파일 읽기
replacement_dict = {}
with open(auto_sim_file_path, 'r', encoding='utf-8') as auto_sim_file:
    for line in auto_sim_file:
        # 공백을 기준으로 나누기
        parts = line.split()
        if len(parts) == 2:
            key = parts[1]
            value = parts[0]
            replacement_dict[key] = value

# data 파일 읽기
with open(data_file_path, 'r', encoding='utf-8') as data_file:
    data_lines = data_file.readlines()

# 변경된 결과를 저장할 리스트
modified_lines = []

# 데이터 파일의 각 줄을 처리
for line in data_lines:
    modified_line = line
    for key, value in replacement_dict.items():
        if key in line:
            modified_line = line.replace(key, f"/{value}/{key.split('/')[-1]}")
            break
    modified_lines.append(modified_line)

# 결과 출력
for line in modified_lines:
    print(line, end='')

# 결과를 파일로 저장하려면 아래 코드 사용
output_file_path = 'path/to/outputfile.txt'
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.writelines(modified_lines)
