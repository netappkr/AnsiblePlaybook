좋다 👍 이건 그냥 README가 아니라
👉 **“엔서블 연동 관점에서 이해 가능한 문서”**로 만들어야 한다

지금 플레이북 구조까지 포함해서
👉 실무용 README 완성본 만들어줄게

---

# 📘 README (Ansible 연동 포함 완성본)

---

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

---

# 🧠 핵심 설계 (중요)

## 1️⃣ 역할 분리 구조

| 단계    | 역할        |
| ----- | --------- |
| scan  | 메타데이터 생성  |
| usage | 실제 데이터 수집 |
| mail  | HTML 생성   |

👉 **각 단계는 서로 독립적으로 동작**

---

## 2️⃣ auto_db.yaml 역할

```yaml
fsx01:/fg2:
  autopath: fg02_dram
  mountpath: fsx01.aws.wyahn.com:/fg2
```

👉 역할:

* SVM + Junction Path → alias 매핑
* mountpath → 도메인 정보 제공

---

## 3️⃣ 메일 경로 생성 방식 (핵심)

최종 메일 상단:

```
fsx01.aws.wyahn.com:/fg02_dram
```

생성 방식:

```
svm_domain + auto_alias
```

👉 svm_domain은 mountpath에서 추출

---

# 🛠 Ansible Playbook 연동 설명

## 🔹 1. ONTAP Volume 조회

```yaml
na_ontap_rest_cli:
```

* 조건 기반 volume 필터링
* analytics_state = on 필수

---

## 🔹 2. getauto 실행

```yaml
command: "getauto auto.{{ item.autopath.automap }}"
```

👉 automount 정보 조회

---

## 🔹 3. auto_db 생성

```yaml
-r build_auto_yaml
```

👉 getauto 결과 → YAML 변환

---

## 🔹 4. scan_objects 생성

```yaml
-r get_scan_object
```

👉 volume + auto_db → 스캔 대상 생성

---

## 🔹 5. usage 수집

```yaml
-r find_and_collect_usage
```

👉 BFS 기반 디렉토리 탐색

---

## 🔹 6. HTML 생성

```yaml
-r build_mail
```

👉 volume 단위 HTML 생성

---

## 🔹 7. 메일 발송

```yaml
mail:
```

👉 volume별 메일 발송

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

---

# ⚠️ 중요 포인트

## 1. auto_db.yaml 필수

없으면 alias 매핑 안됨

---

## 2. key 형식 반드시 유지

```
svm:/junction_path
```

---

## 3. analytics_state = on 필수

FSA API 동작 조건

---

## 4. finger2 필요

```bash
finger2 <uid>
```

👉 사용자 정보 조회

---

# 🔥 설계 의도

* File Lifecycle 관리
* 사용자별 용량 분석
* 불필요 데이터 식별
* 자동 리포트 생성

---

# 🎯 한줄 요약

👉 **Ansible이 전체 파이프라인을 실행하고, Python은 분석 엔진 역할을 한다**


