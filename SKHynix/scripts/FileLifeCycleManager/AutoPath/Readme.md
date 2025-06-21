# AutoPath

```bash
python3 /opt/awx/projects/_12__netappkr_repo/SKHynix/scripts/FileLifeCycleManager/AutoPath/Autopath.py \
--xcpresult /data/vine/Ansible_XCP/xcp_result/SOC/20240701/result/wy_vol.result \
--xcpinfo /data/vine/Ansible_XCP/xcp_result/SOC/20240701/info/wy_vol.info \
--replace /data/vine/Ansible_XCP/xcp_result/SOC/20240701/replace/wy_vol.replace \
--automap library \
--searchdir ANALOG DIGITAL BACKEND ESD CAE IMPLE \
--volumename wy_vol \
--status PASSED \
--skipdedup on
```


## 변경된 파일 예시
```bash
4 /hil013h/sim_cis_hil013h/Test/asd.fsdb
0 /hil013h/sim_cis_hil013h/Test/asd.sp.fsdb
0 /hil013h/sim_cis_hil013h/Test/a.tr
0 /hil013h/sim_cis_hil013h/Test/a.tr0
0 /hil013h/sim_cis_hil013h/Test/qqq.wlf
```