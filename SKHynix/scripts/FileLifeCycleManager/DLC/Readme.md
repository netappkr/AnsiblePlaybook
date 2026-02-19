# DLC.py
SK하이닉스의 넷앱스토리지에 보관된 파일들의 수명주기 관리를 위한 플레이북 보조 스크립트입니다.
스토리지에서 지정한 조건에 맞는 볼륨에서 마운트경로, 부서별 tagging 정보를 출력합니다.
## pre requirement

```
pip install -r requirements.txt
```

## option
3가지 옵션을 가지고 있으며 헬프명령 시 옵션 확인이 가능합니다.
```
python3 FLM.py --help
```
```
usage: FLM.py [-h] [-f FILE [FILE ...]] [-r REQUEST] --config CONFIG

Please refer to Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts

options:
  -h, --help            show this help message and exit
  -f FILE [FILE ...], --file FILE [FILE ...]
                        read filenames example: -f filename1 filename2
  -r REQUEST, --request REQUEST
                        request type
  --config CONFIG       config.yaml
```

1. -f --file 플레이북 실행 시 떨어지는 볼륨정보에 대한 파일 이름입니다.
2. -r --request 플레이북별 요청에 대한 분류입니다.
3. --config FLM 실행에 필요한 설정정보입니다. 플레이북 실행 시 ```config.yaml``` 파일을 읽도록 설정되어 있습니다.

## 사용 예제

```
python3 DLC.py -r get_scan_object --config /tmp/config.yaml -f /tmp/volume_path_info.json
```
```json
[{'mount_path': 'fsx.netappkr.com:/wyahn', 'div': 'wy', 'export_policy': 'exportro_wy', 'xcp_option': {'fmt': "'{} {}'.format(size, x)", 'match': "type == f and fnm('*.txt') or fnm('*.log') or fnm('*.json')"}}, {'mount_path': 'astra-svm.nkic.netappkr.com:/wyfg', 'div': 'wy', 'export_policy': 'exportrw_wy', 'xcp_option': {'fmt': "'{} {}'.format(size, x)", 'match': "type == f and fnm('*.txt') or fnm('*.log') or fnm('*.json')"}}]
```

## 로그파일
FLM.py 실행 시 로그파일을 남깁니다.
1. 경로
```$HOMEdir/logs/flm.log``` 에 남기도록 되어 있으며 경로 변경을 원하신다면 스크립트 내에 로그디렉토리 부분을 수정하실 수 있습니다. 
```
ls -al ~/logs/flm.log
```

2. 로그레벨
로그레벨은 ```info``` 레벨이며 좀 더 자세한 내용은 ```debug```로 설정하신다면 볼 수 있습니다.