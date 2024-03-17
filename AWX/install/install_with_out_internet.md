# AWX 17.1.0 install with out internet

- 최신버전 설치는 K8S 환경에서 오퍼레이터를 이용하여 설치해야 합니다.
- RPM 설치는 [AWX-RPM](https://awx.wiki/installation)에서 찾아볼 수 있습니다만 AWX 정식 배포에 포함된 내용이 아닙니다.

## Architecture
![alt text](./Images/image-1.png)

## 컴퓨팅 최소 조건
설치 환경 및 필수 항목들을 정의합니다.
- OS : centos or redhat 8.x
- CPU : 2 core
- Mem : 4 Mem ( 권장 8)
- Storage: 20GB of space ()
- Running Docker, Openshift, or Kubernetes
If you choose to use an external PostgreSQL database, please note that the minimum version is 10+.

## 환경 구성 가이드
인터넷이 되지 않는 환경에서 설치하는 만큼 필요한 패키지 및 설치를 수동으로 구성해야 합니다.

> ### 경고!
> 해당 가이드는 Red Hat Enterprise Linux release 8.9 (Ootpa) 기준으로 진행되었습니다.

```bash
# cat /etc/*release
NAME="Red Hat Enterprise Linux"
VERSION="8.9 (Ootpa)"
ID="rhel"
ID_LIKE="fedora"
VERSION_ID="8.9"
PLATFORM_ID="platform:el8"
PRETTY_NAME="Red Hat Enterprise Linux 8.9 (Ootpa)"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:redhat:enterprise_linux:8::baseos"
HOME_URL="https://www.redhat.com/"
DOCUMENTATION_URL="https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8"
BUG_REPORT_URL="https://bugzilla.redhat.com/"

REDHAT_BUGZILLA_PRODUCT="Red Hat Enterprise Linux 8"
REDHAT_BUGZILLA_PRODUCT_VERSION=8.9
REDHAT_SUPPORT_PRODUCT="Red Hat Enterprise Linux"
REDHAT_SUPPORT_PRODUCT_VERSION="8.9"
Red Hat Enterprise Linux release 8.9 (Ootpa)
Red Hat Enterprise Linux release 8.9 (Ootpa)
```

### yum local repo 구성
이미 사용중인 ```private repo```가 있다면 그쪽을 이용합니다.
#### 외부망에 접근 가능한 VM
1. 먼저 설치할 환경과 동일한 OS를 설치한 VM 구합니다. 이 VM은 인터넷에 접근가능해야 합니다.

2. Repo 추가 및 ```yum-utils```를 설치합니다.
```bash
sudo yum install yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
sudo 
```
사용한 repo는 아래와 같습니다.
```bash
# yum repolist
Updating Subscription Management repositories.
Unable to read consumer identity

This system is not registered with an entitlement server. You can use subscription-manager to register.

repo id                                       repo name
LocalRepo                                     Local Repository
ansible-2-for-rhel-8-rhui-rpms                Red Hat Ansible Engine 2 for RHEL 8 (RPMs) from RHUI
docker-ce-stable                              Docker CE Stable - x86_64
epel                                          Extra Packages for Enterprise Linux 8 - x86_64
rhel-8-appstream-rhui-rpms                    Red Hat Enterprise Linux 8 for x86_64 - AppStream from RHUI (RPMs)
rhel-8-baseos-rhui-rpms                       Red Hat Enterprise Linux 8 for x86_64 - BaseOS from RHUI (RPMs)
rhui-client-config-server-8                   RHUI Client Configuration Server 8

```
2. ```yumdownloader```를 이용해 필요한 패키지를 다운로드 받습니다.</br>
이렇게 하면 시스템에 맞는 종속성 패키지들까지 한번에 다운로드 받을 수 있습니다.
```
mkdir /var/localrepo
yum install --downloadonly --downloaddir=/var/localrepo --resolve git gcc gcc-c++ nodejs gettext device-mapper-persistent-data lvm2 bzip2 python3.11 python3.11-pip ansible createrepo
yum install --downloadonly --downloaddir=/var/localrepo --resolve docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

3. 다운로드 받은 패키지들을 설치할 서버로 옮깁니다.</br>
**이때 AWX가 설치되는 서버 디렉토리 유무 및 권한이 충분한지 확인 후 실행하세요.**
```bash
scp -i ./ssh/mykey.pem -r /var/localrepo root@awxserver:/var/localrepo
```

#### AWX 서버
4. AWX 서버에 ```createrepo```를 설치합니다.
```bash
mv /var/localrepo
yum -y install createrepo_c-0.17.7-6.el8.x86_64.rpm drpm-0.4.1-3.el8.x86_64.rpm createrepo_c-libs-0.17.7-6.el8.x86_64.rpm
```
5. 로컬레포를 생성합니다.
```bash
createrepo /opt/localrepo/
```
```bash
Directory walk started
Directory walk done - 30 packages
Temporary output repo path: /opt/localrepo/.repodata/
Preparing sqlite DBs
Pool started (with 5 workers)
Pool finished
```
6. 생성한 로컬레포를 등록합니다.
```bash
vi /etc/yum.repos.d/local.repo
```
```ini
[LocalRepo]
name=Local Repository
baseurl=file:///var/localrepo/
enabled=1
gpgcheck=0
```
7. ```LocalRepo``` 등록을 확인합니다.
```bash
dnf repolist
```
```bash
Updating Subscription Management repositories.
Unable to read consumer identity

This system is not registered with an entitlement server. You can use subscription-manager to register.

repo id                                       repo name
LocalRepo                                     Local Repository
ansible-2-for-rhel-8-rhui-rpms                Red Hat Ansible Engine 2 for RHEL 8 (RPMs) from RHUI
epel                                          Extra Packages for Enterprise Linux 8 - x86_64
rhel-8-appstream-rhui-rpms                    Red Hat Enterprise Linux 8 for x86_64 - AppStream from RHUI (RPMs)
rhel-8-baseos-rhui-rpms                       Red Hat Enterprise Linux 8 for x86_64 - BaseOS from RHUI (RPMs)
rhui-client-config-server-8                   RHUI Client Configuration Server 8
```
8. docker compose 명령 구성
curl -SL https://github.com/docker/compose/releases/download/v2.24.7/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

### PIP repo 구성
필요한 패키지 설치를 위해 PIP repo를 구성합니다.

#### 외부망에 접근 가능한 VM
1. ```python3.11```을 설치합니다.
```bash
yum -y install python3.11 python3.11-pip
```
2. pip download 명령을 이용해 필요한 패키지들을 다운로드 받습니다.
```bash
pip3 download pandas>=2.0.0 --dest /var/piprepo
pip3 download pyyaml==5.3.1 --dest /var/piprepo
pip3 download docker-compose>=1.29.1 --dest /var/piprepo
pip3 download docker==6.1.3 --dest /var/piprepo
pip3 download netapp.ontap --dest /var/piprepo
```
3. 다운로드 받은 패키지들을 설치할 서버로 옮깁니다.</br>
**이때 AWX가 설치되는 서버 디렉토리 유무 및 권한이 충분한지 확인 후 실행하세요.**
```bash
scp -i ./ssh/mykey.pem -r /var/piprepo root@awxserver:/var/piprepo
```
4. 필요한 패키지를 설치합니다.
```
pip3 install --no-index --find-links=/var/piprepo requests
pip3 install --no-index --find-links=/var/piprepo netapp.ontap
pip3 install --no-index --find-links=/var/piprepo pandas
```
5. 설치된 package 항목을 확인합니다.
```bash
pip3 list
```
```bash
Package            Version
------------------ --------
ansible            8.3.0
ansible-core       2.15.3
attrs              23.2.0
bcrypt             4.1.2
certifi            2024.2.2
cffi               1.15.1
charset-normalizer 3.3.2
cryptography       37.0.2
distro             1.9.0
docker             6.1.3
docker-compose     1.29.2
dockerpty          0.4.1
docopt             0.6.2
idna               3.6
jsonschema         3.2.0
marshmallow        3.21.1
netapp-ontap       9.14.1.0
packaging          24.0
paramiko           3.4.0
pip                22.3.1
ply                3.11
pycparser          2.20
PyNaCl             1.5.0
pyrsistent         0.20.0
python-dotenv      0.21.1
PyYAML             5.3.1
requests           2.31.0
requests-toolbelt  1.0.0
setuptools         65.5.1
six                1.16.0
texttable          1.7.0
urllib3            2.2.1
websocket-client   0.59.0
```

## Ansible AWX 17.1.0 설치

#### 외부망에 접근 가능한 VM
1. 다음 명령을 사용하여 v17 릴리스를 복제합니다.
```
git clone -b "17.1.0" https://github.com/ansible/awx.git
```
2. 다음 명령을 사용하여 비밀 암호화 키를 생성합니다.
```
openssl rand -base64 30
iR0MXri042xWjgqztRXFK1eLERtU+9g2OhYRVWld
```
3. 디렉터리 로 이동하여 인벤토리awx/installer 파일을 찾습니다.
```
cd awx/installer/
vim inventory
```
4. ```inventory``` 파일에서 아래 항목을 찾아 수정합니다.
```ini
[all:vars]
# Remove these lines if you want to run a local image build
# Otherwise the setup playbook will install the official Ansible images. Versions may
# be selected based on: latest, 1, 1.0, 1.0.0, 1.0.0.123
# by default the base will be used to search for ansible/awx
  dockerhub_base=ansible
# local_docker=true
# your credentials >> Use the key you created with `openssl rand -base64 30`
secret_key=iR0MXri042xWjgqztRXFK1eLERtU+9g2OhYRVWld

admin_user=admin
admin_password=password
```
5. ```inventory``` 파일에서 PostgresSQL 데이터를 보관할 폴더를 ```​/opt/awx```로 변경합니다​.
```ini
postgres_data_dir="/opt/awx/pgdocker"
host_port=80
host_port_ssl=443
#ssl_certificate=
# Optional key file
#ssl_certificate_key=
docker_compose_dir="/opt/awx/awxcompose"
```
6. 여기서 무엇을 선택하든 디렉터리가 존재하고 Docker 사용자가 쓸 수 있는지 확인하세요.
```
sudo mkdir /opt/awx
```
7. git clone 한 경로에서 설치 파일을 몇개 수정해야 합니다.
```
vim installer/roles/local_docker/tasks/main.yml
```
맨윗줄에 추가
```yaml
- name: Install Docker SDK for Python
  ansible.builtin.pip:
    name:
      - "docker==6.1.3"
      - "docker-compose>=1.29"
    extra_args: "--no-index --find-links=/var/piprepo"
```
8. ```​awx/installer/``` 내부에서 Ansible 명령을 따라 Ansible AWX를 설치할 수 있습니다.
```bash
sudo ansible-playbook -i inventory install.yml
```
9. 완료되면 아래와 같이 보입니다.
```bash
docker ps
```
```bash
CONTAINER ID   IMAGE                COMMAND                  CREATED          STATUS          PORTS                                   NAMES
51493254cbdc   ansible/awx:17.1.0   "/usr/bin/tini -- /u…"   40 minutes ago   Up 40 minutes   8052/tcp                                awx_task
ae968ef14f09   ansible/awx:17.1.0   "/usr/bin/tini -- /b…"   40 minutes ago   Up 40 minutes   0.0.0.0:80->8052/tcp, :::80->8052/tcp   awx_web
29bca59e37cc   redis                "docker-entrypoint.s…"   40 minutes ago   Up 40 minutes   6379/tcp                                awx_redis
0c9df9357c63   postgres:12          "docker-entrypoint.s…"   40 minutes ago   Up 40 minutes   5432/tcp                                awx_postgres
```

## Ansible Image Builder
기본 이미지에는 Netapp 플러그인설치가 되어있지 않습니다. 이미지를 수동을 빌드해서 컨테이너를 올려야합니다.
> ### Tips
> Netapp의 엔지니어중 한분이 Netapp-ansible 환경을 실행 할 수 있는 Docker image를 업로드했습니다. 이를 다운로드 받아 사용할 수 있습니다.
> [task_execute_ansible_playbook_using_docker](https://docs.netapp.com/us-en/active-iq/task_execute_ansible_playbook_using_docker.html#before-you-begin)
> 하지만 netapp 모듈 외에 여러 모듈을 사용할 수 있는 ansible 특성상 로컬 서버또는 외부서버에 실행환경을 구성하고 ssh를 통해 연결하는 방법도 있습니다.
> (필요할때 마다 빌드해서 이미지관리하기 너무 귀찮아요..)

1. ```inventory```파일에서 ```dockerhub_base=ansible```을 찾아 주석처리해야합니다. ​
2. 아래 파일을 편집합니다.
```
/opt/awx/installer/roles/image_build/templates/Dockerfile.j2​ 
```
3. ```Install build dependencies``` 항목을 찾아 그 아래 추가 패키지를 설치를 명령합니다.

### 필요 추가 패키지를 설치
필요한 추가 패키지를 설치 하도록 install Playbook에 등록된 도커파일을 수정합니다.
```dockerfile
RUN dnf -y install libxslt-devel \
    libxml2-devel
RUN dnf -y groupinstall 'Development Tools'

RUN python3 -m ensurepip && pip3 install "virtualenv < 20"
RUN pip3 install netapp.ontap
```
## Playbook local 저장소 활용하기
일반적으로 로드하면 로컬레포를 지정할 수 없는 상태로 표기됩니다.

1. 인벤토리 파일 수정
```ini
# AWX project data folder. If you need access to the location where AWX stores the projects
# it manages from the docker host, you can set this to turn it into a volume for the container.
#project_data_dir=/var/lib/awx/projects
project_data_dir=/opt/awx/projects
```

2. 인스톨 재실행
```
sudo ansible-playbook -i inventory install.yml
```

# 참조
- [AWX 17.1.0 install guide](https://github.com/ansible/awx/blob/17.0.1/INSTALL.md)
- [RHEL8에 Ansible Tower(Docker의 AWX) 설치](https://mpolinowski.github.io/docs/DevOps/Ansible/2021-04-28-ansible-tower-rhel/2021-04-28/)
- [구성 오류 - kwargs_from_env()에 성공하지 못했습니다. 'ssl_version이 있습니다.](https://github.com/geerlingguy/internet-pi/issues/567)
- [[버그] "pip install docker-compose"가 debian 12에서 실패합니다.](https://github.com/docker/compose/issues/11168)
- [Ansible tower 요구사항](https://docs.ansible.com/ansible-tower/latest/html/installandreference/requirements_refguide.html#ansible-software-requirements)
- [task_execute_ansible_playbook_using_docker](https://docs.netapp.com/us-en/active-iq/task_execute_ansible_playbook_using_docker.html#before-you-begin)