# Ansible 보조 스크립트
Ansible 모듈이 제공하는 기능만으로는 디테일한 설정이 불가능하거나 외부 시스템과 연동이 필요한 상황에 어려움이 있을 수 있습니다.</br>
이를 보조하기위한 파이썬 스크립트를 작성하여 활용합니다.

## requirement
이 부분은 엔서블플레이북이 스크립트 실행에 필요한 패키지를 다운로드 받도록 설정하고있습니다.</br>
하지만 repo에 접근하지못하는 환경의 경우 패키지를 수동설치해야 합니다.

pip를 이용한 요구사항 설치 명령
```
pip install -r requirements.txt
```

# install
프로젝트 진행에 따라 필요 시 스크립트를 업데이트할 예정입니다.
```git clone``` 명령을 통해 소스를 다운로드 받습니다.

## generate_table.py
스크립트 사용법을 소개합니다.

### help 명령
```--help``` 옵션을 통해 스크립트에 필요한 인수를 확인합니다.
```PS
PS C:\Users\wooyeoun\OneDrive\자료\11. Netapp\NetappKR Github\AnsiblePlaybook> python .\SKHynics\scripts\generate_table.py --help
usage: generate_table.py [-h] [-f FILE] [-r REQUEST]

Please refenace Netapp korea github : https://github.com/netappkr/AnsiblePlaybook/tree/main/SKHynics/scripts

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  read filename
  -r REQUEST, --request REQUEST
                        request type
```
### 실행 예제
1. ansible playbook ```GetInodebyVolume.yaml``` 연계
예제파일에서 ```testinpu.json``` 에 담겨있는 Cluster 내 볼륨별 inode 정보를 Html Table 형식으로 변환하여 출력합니다, 
```ps
python .\SKHynics\scripts\generate_table.py -r volume_indoe_info -f .\SKHynics\scripts\testinput.json
```
출력
```html
    <html>
    <head></head>
    <body>
      <table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th>Volume Name</th>
      <th>Total Inodes</th>
      <th>Used Inodes</th>
      <th>Free Inodes</th>
      <th>Inode Use%</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>catalog</td>
      <td>31122</td>
      <td>104</td>
      <td>31018</td>
      <td>0.33</td>
    </tr>
    <tr>
      <td>vol2</td>
      <td>311287</td>
      <td>98</td>
      <td>311189</td>
      <td>0.03</td>
    </tr>
    <tr>
      <td>fsx_root</td>
      <td>31122</td>
      <td>105</td>
      <td>31017</td>
      <td>0.34</td>
    </tr>
    <tr>
      <td>vol1</td>
      <td>31876709</td>
      <td>97</td>
      <td>31876612</td>
      <td>0.00</td>
    </tr>
  </tbody>
</table>
    </body>
    </html>
```
2. ansible playbook ```GetInodebyCluster.yaml``` 연계
```ps
python .\SKHynics\scripts\generate_table.py -r clusters_inode_info -f .\SKHynics\scripts\testinput2.json
```

출력
```html
    <html>
    <head></head>
    <body>
      <table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
    </tr>
  </thead>
  <tbody>
  </tbody>
</table>
    </body>
    </html>
```
### 스크립트 동작로그
```generate_table.log``` 파일에 실행로그를 남기고 있습니다. 에러 발생 시 이 로그파일을 참조합니다.

# 참조
