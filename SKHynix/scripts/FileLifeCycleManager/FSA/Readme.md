# 📊 FSA (File System Analytics) Usage Collector

ONTAP File Analytics API를 활용하여 특정 디렉토리 구조를 탐색(BFS)하고,
사용자별 디렉토리 사용량을 수집하여 HTML 리포트 및 이메일로 전달하는 자동화 시스템입니다.

---

# 🧱 아키텍처 개요

```id="arch01"
Ansible Playbook
        ↓
     FSA.py
        ↓
  ONTAP REST API
        ↓
     finger2 (user lookup)
        ↓
   HTML Report → Email
```

---

# 🚀 주요 기능

* ONTAP Volume 정보 조회
* BFS 기반 디렉토리 탐색 (최대 depth 7)
* Target 디렉토리 자동 탐색
* 사용자별 디렉토리 usage 수집
* owner_id → 사용자 이름 / 이메일 매핑
* HTML 리포트 생성 및 메일 발송

---

# 📁 작업 디렉토리

```id="dir01"
/tmp/fsa/
 ├── volume.json
 ├── config.yaml
 ├── scan_objects.yaml
 ├── usage.yaml
```

> 실행 시 항상 overwrite 됩니다.

---

# ⚙️ Ansible 플레이북 연동

## 📌 사용 플레이북

```id="playbook01"
GetFSADirInfo.yaml
```

---

## 📌 전체 실행 흐름

```id="flow01"
1. ONTAP volume 조회
2. volume.json 생성
3. config.yaml 생성
4. scan_objects 생성 (get_scan_object)
5. BFS 탐색 + usage 수집 (find_and_collect_usage)
6. usage.yaml 생성
7. HTML 생성 (build_mail)
8. 이메일 발송
```

---

## 📌 핵심 Task

```yaml id="ansible01"
- name: Collect usage
  command: >
    python3 {{ fsa_path }}
    -r find_and_collect_usage
    -f {{ work_dir }}/scan_objects.yaml
```

---

# 🧪 Python 단독 실행 방법

## 1️⃣ scan_object 생성

```bash id="run01"
python3 FSA.py -r get_scan_object \
  --config config.yaml \
  -f volume.json
```

---

## 2️⃣ usage 수집 (핵심)

```bash id="run02"
python3 FSA.py -r find_and_collect_usage \
  -f scan_objects.yaml
```

---

## 3️⃣ HTML 리포트 생성

```bash id="run03"
python3 FSA.py -r build_mail \
  -f usage.yaml
```

---

# 📄 config.yaml 예시

```yaml id="cfg01"
division:
  - name: DRAM
    fsa_option:
      path:
        - dir: USER
        - dir: FE
```

---

# 📄 usage.yaml 예시

```yaml id="usage01"
- division: DRAM
  volume: vol2
  user_dir: hanmin
  full_path: /USER/hanmin
  owner_id: 0
  user_name: root
  email: system@sk.com
  bytes_used: 10568507392
```

---

# 🔍 핵심 로직 설명

## 📌 BFS 탐색

* `/`부터 시작하여 디렉토리 순회
* 최대 depth 7까지 탐색
* target 발견 시 하위 디렉토리만 조회

---

## 📌 full_path 생성 방식

ONTAP API 특성상 full path는 직접 생성해야 함

```id="logic01"
full_path = parent.rstrip("/") + "/" + name
```

---

## 📌 탐색 방식

```id="logic02"
/ → USER 발견
→ /USER 하위 조회
→ /USER/{user_dir} 수집
```

---

# 👤 사용자 정보 조회

```bash id="user01"
finger2 <owner_id>
```

---

## 📌 출력 예시

```id="user02"
Name : root
E-mail : system@sk.com
```

---

## 📌 파싱 방식

```python id="user03"
Name\s*:\s*(.*)
E-mail\s*:\s*(.*)
```

---

# 📧 HTML 리포트

* 사용자별 디렉토리 사용량
* GB 단위 변환
* 이메일 포함
* 테이블 형태 출력

---

# ⚠️ 주의사항

## 1️⃣ ONTAP API 구조

* `path` = 부모 경로
* `name` = 디렉토리 이름
* full_path 직접 생성 필요

---

## 2️⃣ owner_id 주의

```text id="warn01"
owner_id = 0 → system/root 계정
```

---

## 3️⃣ finger2 의존성

* OS에 설치 필요
* 환경별 출력 포맷 다를 수 있음

---

## 4️⃣ Ansible YAML 저장

반드시 변환 필요

```yaml id="warn02"
content: "{{ usage_result.stdout | from_yaml | to_nice_yaml }}"
```

---

# 🔥 성능 특징

* BFS + 즉시 수집 구조
* API 호출 최소화 (약 50% 감소)
* 중복 제거 (seen_paths)
* depth 제한으로 과도한 탐색 방지

---

# 🚀 향후 개선 항목

* Top N 사용자 리포트
* 용량 임계치 알림
* 사용자별 개별 메일 발송
* user_db.yaml 기반 lookup (finger 제거)
* 캐싱 적용 (finger 호출 최적화)

---

```


