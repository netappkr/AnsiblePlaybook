# 📘 finger2 - User Lookup CLI Tool
하이닉스 환경과 동일한 환경 생성을 위해 테스트 용으로 스크립트 작성
## 🧾 개요

`finger2`는 ONTAP FSA에서 조회한 `owner_id`를 기반으로  
사용자 정보를 조회하고 이메일을 확인할 수 있는 **CLI 도구**입니다.

기존 `finger` 명령어처럼 사용할 수 있도록 설계되었으며,  
YAML 기반 사용자 DB를 활용하여 간단하고 빠르게 조회할 수 있습니다.

---

## 🎯 주요 기능

- 🔍 사용자 ID 기반 정보 조회
- 📄 전체 사용자 목록 조회 (`list`)
- 📧 이메일 정보 확인
- ⚙️ YAML 기반 사용자 데이터 관리
- 🧩 FSA / 자동화 스크립트와 연동 가능

---

## 📦 설치 방법

### 1️⃣ 스크립트 설치

```bash
cp finger2 /usr/local/bin/
chmod +x /usr/local/bin/finger2
```
### 2️⃣ 사용자 DB 위치
```bash
mkdir -p /etc/finger2
cp user_db.yaml /etc/finger2/
```

### 📁 디렉토리 구조
```bash
/usr/local/bin/finger2
/etc/finger2/user_db.yaml
```

## 🧑‍💻 사용 방법

### 🔹 1. 사용자 조회
```bash
finger2 00000001
```
출력 예시:
```bash
Login name : 00000001
Employee ID : 0000005
Name : 아무개(TL)
Dept. : HBM DV
Job position : Part 장
Workstate : C
E-mail : aaaaa@sk.com
Home : /home/tdesign/td0000005
Shell : /sbin/nologin
```

### 🔹 2. 사용자 목록 조회
```bash
finger2 list
```
출력 예시:
```bash
Available Users:

00000001   아무개(TL)          aaaaa@sk.com
00000002   홍길동              hong@sk.com
```

### 🔹 3. 사용자 DB 파일 지정
```bash
finger2 00000001 -f /tmp/custom.yaml
```