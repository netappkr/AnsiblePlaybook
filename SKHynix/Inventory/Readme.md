# 인벤토리
플레이북의 설정파일입니다.

## 실행 명령
```
ansible-playbook -i inventory파일이름 playbook파일이름
```
## AWX에서 인벤토리 설정
호스트별 실행 변수를 다르게 설정하였습니다.

각 플레이북 별로 바라보고 있는 host가 다르며 해당 호스트는 플레이북 실행 시 올바른 변수를 제공해야합니다.

### task_server_1
일반적으로 사용하시던 클러스터의 정보를 읽어 메일로 리포트를 보내는데 사용합니다.

활용되는 플레이북
- GetInodebyCluster.yaml
- GetInodebyVolume.yaml
- GetSnapmirrorStatus.yaml
- GetSpaceUsagebyAggr_and_Volume.yaml
- GetSpaceUsageByAggr.yaml
- GetSpaceUsageByVolume.yaml

### task_server_1_Soc
SoC 자산의 클러스터에서 정보를 읽어 메일로 리포트를 보내는데 사용합니다.

활용되는 플레이북
- GetSpaceUsagebyAggr_and_Volume_in_Soc.yaml

### task_server_1_flm
파일 수명주기 관리를 위해 사용되는 호스트입니다.

활용되는 플레이북
- FileLifeCycleManage.yaml