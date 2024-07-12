# 파일 라이프 사이클 관리
xcp 스캔을 사용하여 운영에 필요한 File 수명주기 관리 기능을 구현하는 스크립트 입니다.

### 경고
xcp 스캔을 이용하여 file 정보를 주기적으로 수집하는 행위는 일반적으로 권장하지 않습니다.
이번처럼 특수한 상황이 아니라면 스토리지에서 제공하는 [ NetApp ONTAP File System Analytics ](https://docs.netapp.com/us-en/ontap/concept_nas_file_system_analytics_overview.html#learn-more-about-file-system-analytics) 기능을 이용하여 구현하는 것을 권장합니다.

## 동작 방식 설명
![FLM](./Images/FLM.png)


# 참조
- [ NetApp DoC ONTAP File System Analytics ](https://docs.netapp.com/us-en/ontap/concept_nas_file_system_analytics_overview.html#learn-more-about-file-system-analytics)
- [ NetApp ONTAP File System Analytics Technical Presentation](./Images/NetApp%20ONTAP%20File%20System%20Analytics%20Technical%20Presentation%20(3).pdf)