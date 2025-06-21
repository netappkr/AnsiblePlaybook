# File Life Cycle Manager
오브젝트 스토리지 처럼 블록스토리지에 있는 파일도 라이프사이클을 관리하여 스토리지 공간 효율을 극대화 하기위한 노력

> ### 경고
> ontap은 이미 [File System Analytics](https://docs.netapp.com/us-en/ontap/concept_nas_file_system_analytics_overview.html) 기능이 있습니다. Script를 활용하는 것보다 이것을 활용하는것이 맞습니다.
> 고객측의 특수한 사정으로 이를 활성화하지 않습니다. 하지만 블록스토리지의 File 레벨 정보를 얻어야하는 경우 이것을 활성화하는 것이 맞습니다.
> 스크립트 방식과 [File System Analytics](https://docs.netapp.com/us-en/ontap/concept_nas_file_system_analytics_overview.html) 모두 파일 스캔에 Storage I/O를 사용합니다. 운영팀에서 적용할때는 모니터링을 통해 가장 부하가 적은 시간에 scan 수행하도록 설정하는것이 좋습니다.

## 고객사 파일관리 기준
1. 사업부별로 file 관리가 이루어져야 합니다. 
    - sim1
    - sim2 
    - sim3 
    - soc

2. 관리 대상 볼륨 분로  
    - Cluter 에서 볼륨의 Export Policy 를 확인 하여, 대상 볼륨 확인 (예외 볼륨 개별 처리)
    - Volume Naming 기준 사업부별 볼륨 List 확인 (예외 볼륨 개별 처리)
    - 운영팀에서 Test를 위해 생성한 임의 볼륨을 제외해야 함

3. Ontap DataLIF 확인
사내 DNS 서버를 통하여 DataLIF를 관리하고 있습니다.
볼륨 마운트 시 아래와 같은 규칙을 사용합니다.
   - NFS server : {{clustername}}.chopincad.com

4. XCP Scan 수행  
XCP 툴의 Scan 기능을 활용하여 엔서블 서버에서 스토리지 볼륨내 디렉토리와 파일정보를 스캔합니다.
   - 사업부 또는 특정 리소스별 유휴 시간대가 다릅니다. ```XCP Scan``` 동작은 유휴 시간에 이루어져야 합니다.  
   - XCP 명령문에 특정 확장자에 대해서만 스캔해야합니다.  
   - XCP 스캔결과에 파일 경로와 Size가 포함되어 있어야 합니다. 
   - 사업부별 정의된 USER Dir 절대 경로로 Grep(Config File 로 정의 하여 필터링 수행) 
   - 파일 경로를 Auto.Path 기준으로 수정 (/data/vine/getauto auto.${AutoMap} )
     ```projectname nsim2m14.Custom.com:/sim_dram_projectname```
   - XCP Scan 작업에 대한 로그를 남겨야합니다.
     Log는 날짜/Volume Dir 형태로 생성
    ```log
    Log/20240502/dram/sim_pl512gtlc/Size
    Log/20240502/dram/sim_pl512gtlc/LIST

    nsimtc.chopincad.com:/vol_name
    nsim2m14.chopincad.com:/vol_name
    nsim3tc.chopincad.com:/vol_name
    nipcontc.chopincad.com:/vol_name
    ```
     XCP Status Fail 시 Mailing 

5. 모든 XCP Scan 완료 여부 확인 하여, Summary Mail 발송 
   - 사업부별 Mailing Total 용량 / 파일 개수  
   - 프로젝트별 메일에 Total / 파일개수   
   - 최종 task 관련 실행 결과 리포팅

6. 예외 처리 
   - 스크립트 안정성을 위한 예외 처리  
     * ssh 를 통한 Cluster 접속 실패 Case 에 대한 예외 처리 
     * LSF 에 대한 예외 처리? 
7. 로그 보관 기간(협의 필요) 후 자동 삭제    
 


### export Policy list
```
nsimtc::>                 export-policy show
Vserver          Policy Name
---------------  -------------------
nsimtc_s3svm1    default
nsimtc_svm0      default_old
nsimtc_svm0      default_rw
nsimtc_svm0      effi_ro
nsimtc_svm0      exportro
nsimtc_svm0      exportro_cis
nsimtc_svm0      exportro_dram
nsimtc_svm0      exportro_nand
nsimtc_svm0      exportrw_cis
nsimtc_svm0      exportrw_dram
nsimtc_svm0      exportrw_nand
nsimtc_svm0      exportrw_new
nsimtc_svm0      exportrw_soc
nsimtc_svm0      exportrw_td
nsimtc_svm0      no_access
nsimtc_svm0      shkang_del230612
nsimtc_svm0      sim_designschool
nsimtc_svm0      sim_dram_al16gd4
nsimtc_svm0      sim_dram_al8gd4b
nsimtc_svm0      sim_dram_ef256gtv
nsimtc_svm0      sim_dram_ef256gtv_ro
nsimtc_svm0      sim_dram_lc24ghbm3a
nsimtc_svm0      sim_dram_psasi
nsimtc_svm0      sim_dram_rg16gd4
nsimtc_svm0      sim_dram_rg16ghbmtv_ro
nsimtc_svm0      sim_dram_scco512md4
nsimtc_svm0      sim_flash_fdesignstd
nsimtc_svm0      sim_nand_hetvnand
nsimtc_svm0      sim_nand_hetvnand_ro
nsimtc_svm0      sim_nand_op1ttlc
nsimtc_svm0      sim_nand_qs4gslc
nsimtc_svm0      sim_nand_qs4gslc_ro
nsimtc_svm0      sim_nand_qs4gslcspi
nsimtc_svm0      sim_nand_qs4gslcspi_ro
nsimtc_svm0      sim_nand_sipisim
nsimtc_svm0      sim_spot_dram_fadesign
36 entries were displayed.

nsim2m14::> export-policy show
Vserver          Policy Name
---------------  -------------------
nsim2m14_s3svm1  default
nsim2m14_svm0    chopin1
nsim2m14_svm0    default
nsim2m14_svm0    default_rw
nsim2m14_svm0    exportro_dram
nsim2m14_svm0    exportro_nand
nsim2m14_svm0    exportrw_cis
nsim2m14_svm0    exportrw_dram
nsim2m14_svm0    exportrw_nand
nsim2m14_svm0    no_access
nsim2m14_svm0    sim_nand_he1ttlcdv
nsim2m14_svm0    sim_nand_op2tqlc
12 entries were displayed.

nsim3tc::> export-policy show
Vserver          Policy Name
---------------  -------------------
nsim3tc_svm0     default
nsim3tc_svm0     default_rw
nsim3tc_svm0     exportro_cis
nsim3tc_svm0     exportro_dram
nsim3tc_svm0     exportro_nand
nsim3tc_svm0     exportrw_cis
nsim3tc_svm0     exportrw_dram
nsim3tc_svm0     exportrw_nand
nsim3tc_svm0     exportrw_td
nsim3tc_svm0     sim_dram_lc24ghbm4c
nsim3tc_svm0     vdb
11 entries were displayed.

nipcontc::> export-policy show
Vserver          Policy Name
---------------  -------------------
nipcontc_svm0    admin
nipcontc_svm0    cis_roswell2p5_ro
nipcontc_svm0    cis_roswell7
nipcontc_svm0    data_ds2
nipcontc_svm0    data_ipvip
nipcontc_svm0    data_t_vendor
nipcontc_svm0    default
nipcontc_svm0    default_old
nipcontc_svm0    default_ro1_new
nipcontc_svm0    default_rw
nipcontc_svm0    default_rw1
nipcontc_svm0    default_rw1_new
nipcontc_svm0    default_rw1_new1
nipcontc_svm0    dram_t12ratelana
nipcontc_svm0    dram_t12ratelimpl
nipcontc_svm0    dsolution_elnido
nipcontc_svm0    dsolution_fransisco
nipcontc_svm0    exportro_socgdesign
nipcontc_svm0    exportro_t1ip
nipcontc_svm0    exportrw_socgdesign
nipcontc_svm0    exportrw_t1ip
nipcontc_svm0    fsolution_excalibur_revision
nipcontc_svm0    ipexportro_new
nipcontc_svm0    ipexportrw
nipcontc_svm0    ipexportrw_new
nipcontc_svm0    nand_panama
nipcontc_svm0    nand_panama_ro
nipcontc_svm0    no_access
nipcontc_svm0    soc_alistar
nipcontc_svm0    soc_arieslite
nipcontc_svm0    soc_doha4
nipcontc_svm0    soc_panama2
nipcontc_svm0    soc_tsmc_dk
nipcontc_svm0    soc_viking
nipcontc_svm0    soc_vikingnew2
nipcontc_svm0    spot_FC_EVAL
nipcontc_svm0    spot_dramimpl
nipcontc_svm0    spot_jenkinsdv
nipcontc_svm0    spot_jitter_eval
nipcontc_svm0    spot_primetime_spice
nipcontc_svm0    spot_tempus_eval
41 entries were displayed.
```

## xcp 스캔 예시
```
[root@linuxhost]#  ./xcp scan -match "type == f and modified > 1*day and fnm('*.fsdb') or fnm('*.tr') or fnm('*.wlf') or fnm('*.tr[0-9]')" -fmt "'{} {}'.format(size, x)" t1nwezondns01:/dhmin_fg_capa_test_20240110 > /data/vine/hm_test/dlc_test/log1 2>> /data/vine/hm_test/dlc_test/log2
XCP 1.6.3; (c) 2024 NetApp, Inc.; Licensed to KICHUL NAM [NetApp Inc] until Sat Sep 14 15:24:11 2024

0 t1nwezondns01:/dhmin_fg_capa_test_20240110/asd.tr0
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/asd.tr1
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/asd.tr2
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/asd.tr3
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/asd.tr4
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/asd.trn.tr1
4 t1nwezondns01:/dhmin_fg_capa_test_20240110/Test/asd.fsdb
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/Test/asd.sp.fsdb
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/Test/a.tr
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/Test/a.tr0
0 t1nwezondns01:/dhmin_fg_capa_test_20240110/Test/qqq.wlf

Filtered: 11 matched, 6309 did not match

Xcp command : xcp scan -match type == f and modified > 1*day and fnm('*.fsdb') or fnm('*.tr') or fnm('*.wlf') or fnm('*.tr[0-9]') -fmt '{} {}'.format(size, x) t1nwezondns01:/dhmin_fg_capa_test_20240110
Stats       : 6,320 scanned, 11 matched
Speed       : 1.16 MiB in (1.27 MiB/s), 22.0 KiB out (24.1 KiB/s)
Total Time  : 0s.
STATUS      : PASSED
```