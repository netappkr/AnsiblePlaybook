## 📌 개요

이 프로젝트는 **ONTAP FSA(File System Analytics)** 데이터를 기반으로
사용자별 디렉토리 사용량 및 증감량을 분석하고
HTML 리포트를 생성하여 메일로 발송하는 자동화 도구입니다.

👉 본 스크립트는 **Ansible Playbook과 연계되어 실행됩니다.**

---

## 🧩 전체 아키텍처

```
Ansible Playbook
   ↓
ONTAP API + getauto 실행
   ↓
FSA.py (Python)
   ↓
HTML 생성
   ↓
메일 발송
```

---

## ⚙️ 실행 흐름 (핵심)

플레이북 기준 전체 흐름 👇 

```
1. ONTAP Volume 조회
2. getauto 실행 (Auto Mount 정보 수집)
3. auto_db.yaml 생성
4. scan_objects 생성
5. 디렉토리 usage 수집
6. HTML 생성
7. 메일 발송
```

---

## 🔄 상세 처리 흐름

```
volume.json (ONTAP API)
auto_raw.json (getauto 결과)
   ↓
[build_auto_yaml]
   ↓
auto_db.yaml
   ↓
[get_scan_object]
   ↓
scan_objects.yaml
   ↓
[find_and_collect_usage]
   ↓
usage_latest.yaml
   ↓
[build_mail]
   ↓
mail.yaml
   ↓
[Ansible mail module]
```
## 역할 분리 구조

| 단계    | 역할        |
| ----- | --------- |
| scan  | 메타데이터 생성  |
| usage | 실제 데이터 수집 |
| mail  | HTML 생성   |

**각 단계는 서로 독립적으로 동작합니다*

## auto_db.yaml
사내 autopath 명령어 출력결과를 가공하여 저장합니다. 

👉 역할:
* SVM + Junction Path → alias 매핑
* mountpath → 도메인 정보 제공


# 🛠 Ansible Playbook 연동 설명
## 🔹 1. ONTAP Volume 조회
```yaml
na_ontap_rest_cli:
```
* cli 명령어, 조건 기반 volume 필터링
* analytics_state = on 필수

## 🔹 2. getauto 실행
```yaml
command: "getauto auto.{{ item.autopath.automap }}"
```
### 출력예시
```sh
=== auto.sim ===
fg_vol_dram svm_CVO2.aws.wyahn.com:/fgvol
vol1_dram svm_CVO2.aws.wyahn.com:/vol1
vol2_dram svm_CVO2.aws.wyahn.com:/vol2
fg02_dram fsx01.aws.wyahn.com:/fg2
```
👉 automount 정보 조회

## 🔹 3. auto_db 생성

```bash
python3 /opt/awx/projects/_12__netappkr_repo/SKHynix/scripts/FileLifeCycleManager/FSA/FSA.py -r build_auto_yaml -f /tmp/fsa/auto_raw.json --debug
```
### 출력예시
```yaml
sim:
  svm_CVO2:/fgvol:
    autopath: fg_vol_dram
    mountpath: svm_CVO2.aws.wyahn.com:/fgvol
  svm_CVO2:/vol1:
    autopath: vol1_dram
    mountpath: svm_CVO2.aws.wyahn.com:/vol1
  svm_CVO2:/vol2:
    autopath: vol2_dram
    mountpath: svm_CVO2.aws.wyahn.com:/vol2
  fsx01:/fg2:
    autopath: fg02_dram
    mountpath: fsx01.aws.wyahn.com:/fg2
```
👉 getauto 결과 → YAML 변환

---

## 🔹 4. scan_objects 생성

```bash
python3 /opt/awx/projects/_12__netappkr_repo/SKHynix/scripts/FileLifeCycleManager/FSA/FSA.py -r get_scan_object --config /tmp/fsa/config.yaml -f /tmp/fsa/volume.json --auto-db /tmp/fsa/auto_db.yaml --debug
```

👉 volume + auto_db → 스캔 대상 생성

---

## 🔹 5. usage 수집

```bash
python3 /opt/awx/projects/_12__netappkr_repo/SKHynix/scripts/FileLifeCycleManager/FSA/FSA.py -r find_and_collect_usage -f /tmp/fsa/scan_objects.yaml --prevfile /tmp/fsa/usage_latest.yaml
```

👉 BFS 기반 디렉토리 탐색

---

## 🔹 6. HTML 생성

```bash
python3 /opt/awx/projects/_12__netappkr_repo/SKHynix/scripts/FileLifeCycleManager/FSA/FSA.py -r build_mail -f /tmp/fsa/usage.yaml
```

👉 volume 단위 HTML 생성

---


# 📂 주요 파일 설명

| 파일                | 설명       |
| ----------------- | -------- |
| FSA.py            | 핵심 로직    |
| config.yaml       | 필터 및 설정  |
| auto_db.yaml      | alias 매핑 |
| scan_objects.yaml | 스캔 대상    |
| usage.yaml        | 사용량 데이터  |
| mail.yaml         | 메일 결과    |

---

# 📊 데이터 구조

## scan_objects.yaml

```yaml
- vserver: fsx01
  svm_domain: fsx01.aws.wyahn.com
  volume: fg02
  auto_alias: fg02_dram
```

---

## usage.yaml

```yaml
- volume: fg02
  auto_alias: fg02_dram
  svm_domain: fsx01.aws.wyahn.com
  user_dir: USER1
  bytes_used: 123456789
```

---

## mail.yaml

```yaml
- volume: fg02_dram
  emails:
    - user@company.com
  html: "<html>...</html>"
```

---

# 🚀 실행 방식
👉 사용자는 직접 실행하지 않음
👉 **Ansible Playbook을 통해 자동 실행됨**

```bash
ansible-playbook fsa.yml
```


