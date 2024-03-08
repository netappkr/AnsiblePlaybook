# Ansible 이란?
<p align="center">
  <img src="./Images/ansble.png">
</p>
Ansible은 파이썬 기반으로 작성되었으며, module과 명령어를 사용하여 여러 서버에 동시에 명령을 실행할 수 있는 자동화 엔진입니다. </br>
또한 ```ansible playbook``` 이라는 스크립트를 통해 IT 어플리케이션 인프라스트럭쳐를 정확하게 묘사할 수 있는 언어입니다. </br>
원래 무료 오픈소스 프로젝트였으나 레드햇이 인수하여 오픈소스쪽과 별개로 Redhat에서 Ansible 자동화 솔루션을 판매하고 있습니다. </br>

레드헷이 운영하는 버전과 커뮤니티 버전이 있의며 그 둘의 차이는 크게 없으나 엔서블관련 공식 기술지원을 받을 수 있는 여부에 차이가 있습니다.</br>
( 역시 돈이 최고인가봐요...)

## AWX로 Ansible Playbook 관리
AWX 또한 커뮤니티 버전과 레드헷의 Ansible Tower 로 나뉩니다.
엔서블과 마찬가지로 기능은 거의 비슷합니다. 커뮤니티 버전의 이용 가이드를 Ansible Tower의 문서를 참조할 정도입니다.

## Netapp.ontap Ansible 모듈
Netapp의 엔지니어분들 또한 Ansible에 모듈제작 및 배포에 공헌하고 있으며 이분들 덕분에 Netapp을 사용하시는 모든 Client 들이 Ansible을 통해 자동화된 스토리지 운영을 하고 있습니다.
이를 통해 반복되는 작업을 자동화 및 관리하고 스토리지 자원들을 엔서블이 지원하는 여려 모듈들과 함께 통합 관리 할 수 있습니다.

# Ansible support
모든 IaC 툴들이 그렇듯 이것을 이용하는 사용자는 몇몇 개념에 대한 숙지가 필요합니다.
Netapp Korea PSE 분들은 Netapp의 파트너분들이나 고객분들이 Ansible을 업무에 쉽게 적용하실 수 있도록 도움을 드리고 있습니다.

## Ansible Testbed
[awx.netappkr.com](awx.netappkr.com)

# 참고
- [Ansible Netapp.ontap](https://docs.ansible.com/ansible/latest/collections/netapp/ontap/index.html)
- [Netapp blog Learn how to Ansible](https://www.netapp.com/ko/devops-solutions/ansible/)
