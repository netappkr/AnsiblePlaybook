# 📦 FSA Directory Usage Analyzer

NetApp ONTAP FSA(File System Analytics) API를 활용하여
**USER 디렉토리 하위 사용량을 분석하고, 사용자별 이메일 매핑 및 HTML 리포트를 생성하는 도구**

---

# 🚀 Overview

이 스크립트는 다음과 같은 흐름으로 동작합니다:

```
ONTAP Volume → USER 디렉토리 탐색 → 하위 디렉토리 usage 조회
→ owner_id 기반 사용자 정보 조회 → HTML 리포트 생성
```

---

# 🏗️ Architecture

```
[scan object JSON]
        ↓
get_scan_object
        ↓
scan_objects.yaml
        ↓
find_dir
        ↓
found_dirs.yaml
        ↓
get_usage
        ↓
usage.yaml
        ↓
build_mail
        ↓
report.html
```

---

# 📂 Features

* ✅ ONTAP FSA API 기반 디렉토리 분석
* ✅ BFS 기반 USER 디렉토리 자동 탐색
* ✅ 사용자별 용량 집계
* ✅ `owner_id → email` 매핑 (finger2)
* ✅ YAML 기반 데이터 처리 (Ansible 친화)
* ✅ HTML 리포트 생성
* ✅ 상세 로그 (INFO / DEBUG 지원)

---

# ⚙️ Requirements

* Python 3.8+
* requests
* PyYAML
* ONTAP FSA enabled (analytics_state = on)
* Linux 환경 (finger2 사용)

```bash
pip install requests pyyaml
```

---

# 🔧 Configuration (config.yaml)

```yaml
domain: example.com

division:
  - name: SCH
    fsa_option:
      path:
        - dir: USER
```

---

# 📥 Input Data (scan JSON)

ONTAP REST API (`/storage/volumes`) 결과 JSON 필요

---

# 🧪 Usage

## 1️⃣ Scan Object 생성

```bash
python fsa.py -r get_scan_object -f volumes.json --config config.yaml
```

👉 output: `scan_objects.yaml`

---

## 2️⃣ USER 디렉토리 탐색

```bash
python fsa.py -r find_dir -f scan_objects.yaml
```

👉 output: `found_dirs.yaml`

---

## 3️⃣ 사용자 Usage 조회

```bash
python fsa.py -r get_usage -f found_dirs.yaml
```

👉 output: `usage.yaml`

---

## 4️⃣ HTML 리포트 생성

```bash
python fsa.py -r build_mail -f usage.yaml > report.html
```

---

# 📊 Output Example

## YAML

```yaml
- division: SCH
  volume: vol1
  user: wooyoung
  full_path: /data/USER/wooyoung
  owner_id: 1001
  email: wooyoung@company.com
  bytes_used: 104857600
```

---

## HTML

* 사용자별 사용량 테이블
* GB 단위 변환
* 이메일 포함

---

# 🪵 Logging

로그 위치:

```bash
~/logs/fsa.log
```

로그 레벨 설정:

```bash
export LOG_LEVEL=DEBUG
```

로그 예시:

```
[INFO] [START] find_directories
[INFO] [FOUND] /data/USER/wooyoung
[INFO] [QUERY] path=/data/USER count=45
[DEBUG] [USER] wooyoung 123456789 wooyoung@company.com
```

---

# ⚠️ Troubleshooting

## 🔸 API 응답 없음

* ONTAP FSA 활성화 확인 (`analytics_state = on`)
* 네트워크 / 인증 확인

## 🔸 email 조회 실패

* finger2 설치 확인
* owner_id 존재 여부 확인

## 🔸 디렉토리 탐색 안됨

* `fsa_option.path.dir` 값 확인
* BFS depth (기본 7) 초과 여부 확인

---

# 🤝 Ansible Integration

이 스크립트는 각 단계별로 실행 가능하여
Ansible Playbook과 쉽게 연동 가능합니다.

---

# 🔥 Future Enhancements

* 📧 SMTP 기반 메일 자동 발송
* 👤 사용자별 개별 리포트
* 📊 용량 threshold 알림
* ⏱ cron 기반 자동 실행

---

# 🧑‍💻 Author

NetApp Korea Automation Script
Maintained for internal FSA usage analysis

---
