# XCP scan
ontap api만으로는 볼륨 내부 file 레벨의 정보를 얻기가 어렵습니다.</br>
Ansible로 XCP 명령을 실행하여 File 레벨 정보를 얻어와 작업합니다.</br>
ontap에서 file_analytics 를 활성화 하면 rest api를 활용하여 데이터를 가져올 수 있습니다.

![img](https://docs.netapp.com/us-en/netapp-solutions/media/xcp-bp_image2.png)
## xcp Guide
Xcp 설치 및 가이드는 Netapp Docs를 참조하세요.

## Play book에서 활용한 XCP 명령
 
## 참조
- [xcp-bp-file-analytics](https://docs.netapp.com/us-en/netapp-solutions/xcp/xcp-bp-file-analytics.html)
- [data-move-or-migration](https://docs.netapp.com/us-en/netapp-solutions/xcp/xcp-bp-netapp-xcp-overview.html#data-move-or-migration)
- [xcp.ini setting](https://docs.netapp.com/ko-kr/xcp/xcp-configure-the-ini-file-for-xcp-nfs.html#%EB%A3%A8%ED%8A%B8-%EC%82%AC%EC%9A%A9%EC%9E%90%EC%97%90-%EB%8C%80%ED%95%9C-ini-%ED%8C%8C%EC%9D%BC%EC%9D%84-%EA%B5%AC%EC%84%B1%ED%95%A9%EB%8B%88%EB%8B%A4)
- [xcp 설치](https://docs.netapp.com/ko-kr/xcp/xcp-install-xcp.html)
- [file_system_analytics.py](https://github.com/NetApp/ontap-rest-python/blob/master/examples/rest_api/file_system_analytics.py)