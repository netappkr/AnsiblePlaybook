# 기능 요청
용량을 많이 사용하는 사용자 디렉토리를 분석하여 담당자에게 자동으로 안내 메일을 발송하는 시스템

## 개요
현재 운영 중인 프로젝트 볼륨의 사용량을 분석하여\
**용량을 많이 사용하는 디렉토리를 파악하고 담당자에게 이메일로 안내하는 자동화 작업**을 수행한다.

기존에는 `xcp scan`을 사용하여 직접 파일 시스템을 스캔했지만,\
앞으로는 **FSA(File System Analytics) REST API 기반 조회 방식으로 변경**하는 것을 고려하고 있다.
단, **FSA가 적용되지 않은 볼륨은 기존 방식(xcp scan)을 유지**하여 통합적으로 처리할 예정이다.

------------------------------------------------------------------------

# 1. 분석 대상 Volume 선정
먼저 스토리지 내 모든 볼륨 중 **분석이 필요한 프로젝트 볼륨을 선정**한다.

다음 조건을 만족하는 볼륨을 조회한다.
``` bash
vol show -type rw -total >=99TB -volume !*spot*, !fg_oss*, !effi* -logical-used-percent >=80 -is-space-reporting-logical true
```

## 조건 설명
**대용량 프로젝트 볼륨 중 사용률이 높은 볼륨만 선정**한다.

|  조건                                |설명                               |
|  -----------------------------------| -----------------------------------|
|  type rw                            | 읽기/쓰기 볼륨 |
|  total \>= 99TB                     | 전체 용량이 99TB 이상 |
|  logical-used-percent \>= 80        | 사용률 80% 이상 |
|  !*spot*                            | 이름에 spot 포함된 볼륨 제외 |
|  !fg_oss\*                          | fg_oss 관련 볼륨 제외 |
|  !effi\*                            | effi 관련 볼륨 제외 |
|  is-space-reporting-logical true    | logical space reporting 활성화 볼륨 |




# 2. Policy 기준 제외 처리
선정된 볼륨 중에서 **이미 사용 종료된 볼륨을 제외**한다.
다음 Policy가 설정된 볼륨은 분석 대상에서 제외한다.

-   `*_ro`
-   `*_ro1`
-   `*exportro*`
-   `no_access`


# 3. 최종 분석 대상 Volume List 생성

위 조건을 통과한 볼륨들을 **최종 분석 대상 리스트로 생성**한다.

#### 예시
-    vol_project01
-    vol_project02
-    vol_project03

이 리스트를 기반으로 디렉토리 용량 분석을 진행한다.


# 4. 디렉토리 용량 분석
현재는 아래 명령을 사용하여 **볼륨 내부 디렉토리 사용량을 분석**한다.

``` bash
xcp scan -fork -duk
```

## 옵션 설명
|  옵션   |의미 |
| ------| ----------------------|
|  scan  | 파일 시스템 스캔 |
|  fork  | 멀티 스레드 실행 |
|  du    | 디렉토리 사용량 분석 |
|  k     | KB 단위 출력 |

즉, **디렉토리별 용량 정보를 수집**한다.


# 6. 분석 대상 디렉토리 구조
용량 분석 대상 디렉토리는 다음과 같은 구조를 가진다.

#### 예시
volume/SCH/USER

하지만 볼륨마다 **디렉토리 depth가 다를 수 있다.**

#### 예시
-    vol1/SCH/USER
-    vol2/PROJECT/SCH/USER
-    vol3/data/project/SCH/USER

따라서 **볼륨별 분석 depth를 별도 관리할 필요가 있다.**
기존 구별법은
```
특정 볼륨을 지정하여 따로 뎁스체크를 하엿고
일반적으로는 특정 디렉토리를 찾아서합니다.
7뎁스까지 쭉 확인해서 원하는 디렉토리가 일치하는게 있는지 확인이 가능할까요?
```
찾는 단어 키워드는 
- USER
- user
- BE
- FE
- INTERFACE
- WORK_DIR
- DK

------------------------------------------------------------------------

# 7. 디렉토리 사용량 정렬
수집된 디렉토리 정보를 **용량 기준으로 내림차순 정렬**한다.

#### 예시
|  Directory   |Size|
|  ----------- |--------|
|  userA       | 8 TB |
|  userB       | 4 TB |
|  userC       | 500 GB |
|  userD       | 1 GB |

------------------------------------------------------------------------

# 8. 작은 디렉토리 제외
분석 결과 중 **용량이 거의 없는 디렉토리는 제외**한다.

#### 예시
-    1GB 이하 제외

#### 목적
-   의미 없는 데이터 제거
-   실제 용량을 많이 사용하는 사용자만 추출

------------------------------------------------------------------------

# 9. 디렉토리 Owner 확인
fsa api 정보에서 각 디렉토리의 소유자를 확인한다.

#### 예시

``` json
{
  "_links": {
    "next": {
      "href": "/api/resourcelink"
    },
    "self": {
      "href": "/api/resourcelink"
    }
  },
  "num_records": 1,
  "records": [
    {
      "group_id": 30,
      "name": "string",
      "owner_id": 54738,
      "path": "string",
    }
  ]
}
```


------------------------------------------------------------------------

# 10. Owner → 이메일 매핑

디렉토리 owner 계정을 기반으로 **이메일 주소를 조회**한다. 조회방식 확인 필요

이 정보는 다음 방식으로 조회한다.
특정 사내 유저를 조회 할 수 있는 사이트에서 owner_id 값을 활용하여 조회

#### 예시
```bash
finger2 00000001
```
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

------------------------------------------------------------------------

# 11. 결과 데이터 정리

수집된 데이터를 표 형태로 정리한다.

#### 예시

|  Directory   |Size   |Owner   |Email |
|  ----------- |------ |------- |-------------------|
|  USERA       |8TB    |userA   |userA@company.com |
|  USERB       |4TB    |userB   |userB@company.com |

------------------------------------------------------------------------

# 12. 이메일 발송

정리된 결과를 기반으로 **담당자 및 사용자에게 이메일을 발송**한다.

#### 메일 내용 예시
-   디렉토리 사용량
-   사용자 정보
-   정리 요청 안내

각 디렉토리 별 이전 데이터와 비교하여 이전 데이터 증가량이 얼마나 증가했는지가 필요함
이 증감량 기준은 이전에 스크립트가 실행된 시점으로 계산되어야 합니다.

최상위 디렉토리는 auto.sim 명령으로 출력한 디렉토리 이름이 들어가야함
메일 전송 관련 로그가 필요함 이력에 남길 내용 : 메일 전송 정보, 보낸 데이터

<table>
   <tr>
        <th colspan="8">auto.sim 출력 결과</th>
    </tr>
    <tr>
        <th colspan="4">/USER</th>
        <th colspan="4">/FE</th>
    </tr>
    <tr>
        <th>total (GB)</th>
        <th>diff (GB)</th>
        <th>user</th>
        <th>name</th>
        <th>total (GB)</th>
        <th>diff (GB)</th>
        <th>user</th>
        <th>dirname</th>
    </tr>
    <tr>
        <td>29</td>
        <td>1</td>
        <td>1001</td>
        <td>/wooyoung</td>
        <td>29</td>
        <td>1</td>
        <td>1002</td>
        <td>/hanmin</td>
    </tr>
    <tr>
        <td>29</td>
        <td>1</td>
        <td>1001</td>
        <td>/wooyoung</td>
        <td>29</td>
        <td>1</td>
        <td>1002</td>
        <td>/hanmin</td>
    </tr>
</table>


> ### auto.sim 이란? ###
> 하이닉스에 구성된 autofs 구성 정보를 출력 하는 명령어 
> 에시 출력
> ```
> getauto auto.sim
> ```
> ```
> === auto.sim ===
> wooyoung_sim an_svm.nkic.netappkr.com:/wooyoung
> wy_vol2_sim an_svm.nkic.netappkr.com:/wy_vol2
> ```
------------------------------------------------------------------------

# 전체 Workflow 요약

1. 대형 볼륨 조회
    (99TB 이상 + 사용률 80%)

2. 정책 기준 제외
    (ro / no_access)

3. 최종 볼륨 리스트 생성

4. 볼륨별 디렉토리 사용량 분석
    - FSA → REST API
    - non FSA → xcp scan

5. 특정 depth 디렉토리 분석

6. 용량 기준 정렬

7. 작은 디렉토리 제외

8. 디렉토리 owner 확인

9. owner → email 매핑

10. 표 생성

11. 이메일 발송

------------------------------------------------------------------------


