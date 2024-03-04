#!/bin/bash

FALOGPATH="/opt/NetApp/xFiles/xcp/xcpfalogs/xcp_console.log"
INSTALL_LOGPATH="./install.log"
HOST_IP=$(ip route get 8.8.8.8 | sed -n '/src/{s/.*src *\([^ ]*\).*/\1/p;q}')
SSLCERTPATH="/opt/NetApp/xFiles/xcp/server.crt"
SSLPVTKEYPATH="/opt/NetApp/xFiles/xcp/server.key"
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

about()
{
	printf "\n-------------------- $GREEN XCP File Analytics Setup $NC ------------------------------ $NC\n\n"
	printf "      This script must be run from xcp directory containing XCP release files.\n"
	printf "      It installs Postgres DB, Apache Httpd server and\n"
	printf "      copies XCP binaries to appropriate paths.\n"
	printf "      See ./configure -h for other options.\n"
	printf "      Log path: ./install.log\n"
	printf "\n------------------------------------------------------------------------------\n"
}

help() {
	printf "$GREEN\nRun ./configure to setup. (Use below options only if required) $NC\n\n"
	printf "Usage: $0 [option]\n\n"
	printf "   -h      Help\n"
	printf "   -c,     Path to your own SSL certificate file in PEM format.\n"
	printf "   -k,     Path to your own server private key file in .key format.\n"
	printf "   -f,     Clean up and force re-configure system.\n"
	printf "   -d,     Clean up. Delete database, XCP server configurations and unistall packages.\n\n"
	exit 1
}

die()
{
	printf "${RED}$@$NC\n" 1>&2
	exit 1
}

warn()
{
	printf "\n$@\n" 1>&2
}

extra_pkg_installs ()
{
        {
                yum install -y xmlsec1 || die "Unable to install package: xmlsec1. \
Check ./install.log for error details. Either install the package manually or use a different RHEL version."
                yum install -y xmlsec1-openssl || die "Unable to install package: xmlsec1-openssl. \
Check ./install.log for error details. Either install the package manually or use a different RHEL version.";
        } 1>>$INSTALL_LOGPATH 2> >(tee -a $INSTALL_LOGPATH >&2)
}

pkg_remove ()
{
	{
		yum remove -y postgresql-server httpd mod_ssl;
		yum remove -y xmlsec1 xmlsec1-openssl;
	} 1>>$INSTALL_LOGPATH 2> >(tee -a $INSTALL_LOGPATH >&2)
}


cleanup()
{
	warn "Begin cleanup:"
	{
		warn "Stopping services"
		systemctl stop httpd >> /dev/null 2>&1;
		systemctl stop postgresql >> /dev/null 2>&1;
		systemctl stop xcp >> /dev/null 2>&1;
		warn "Removing server configurations"
		/usr/bin/rm -rf /var/www/html/xcp;
		/usr/bin/rm -f /etc/httpd/conf.d/000-xcp.conf;
		warn "Removing Db data"
		/usr/bin/rm -rf /var/lib/pgsql/data;
		warn "Removing xcp binary"
		pkill -f "/usr/bin/xcp --listen";
		/usr/bin/rm -rf /usr/bin/xcp;
	} 1>>$INSTALL_LOGPATH 2> >(tee -a $INSTALL_LOGPATH >&2);
}

userchoice_yesorno()
{
	read -p "Do you wish to continue(y/n):" yn;
	case $yn in
		y) ;;
		n) echo Exiting!; exit;;
		*) echo "Invalid response. Please enter either 'y' or 'n' only.";  exit 1;;
	esac;
}

while getopts ':hc:k:fd' option; do
	case "$option" in
		h) help ;;
		c) USER_CERT=$OPTARG; $echo $cert;;
		k) USER_PVTKEY=$OPTARG; echo $key;
			if [[ -z $USER_CERT ]]; then
				echo "Provide -c <path to cert> first followed by -k <path to key>"
				exit
			fi
			;;
		f) printf "$RED\nCleanup and re-configure the system.$NC\n";
			userchoice_yesorno
			cleanup;
			printf "$RED\nBegin re-confugiration:$NC\n"
			FORCE_INSTALL="true";
			;;
		d) printf "$RED\nCleanup: This will delete - existing database, XCP server configurations,\n"
		   printf "xcp service and remove FA related installed packages.$NC \n";
			userchoice_yesorno
			cleanup;
			warn "Removing packages"
			pkg_remove
			warn "Finished cleanup"
			exit 0
			;;
		:) printf "missing argument for -%s\n" "$OPTARG" >&2
			help ;;
		\?) printf "illegal option: -%s\n" "$OPTARG" >&2
			help ;;

		esac
done
shift $((OPTIND - 1))

if [[ ! -z "$USER_CERT" ]] && [[ -z "$USER_PVTKEY" ]]; then
	die "Pls specify server private key file separately as well using -c option"
fi
if [[ ! -z "$USER_CERT" ]] && [[ ! -z "$USER_PVTKEY" ]]; then
	/usr/bin/cp -f $USER_CERT $SSLCERTPATH
	/usr/bin/cp -f $USER_PVTKEY $SSLPVTKEYPATH
fi

postgress_setup()
{
	{
		if [ -z $FORCE_INSTALL ] && [ -d "/var/lib/pgsql/data" ] && [ -n "$(ls -A "/var/lib/pgsql/data")" ]; then
			systemctl is-active --quiet postgresql.service;
			if [[ $? -gt 0 ]]; then # is-active ret 0 for active >=1 for inactive
				warn "PostgresDb data exists, restarting postgresql service !";
				systemctl restart postgresql.service || die "Error: could not start postgress service.";
				warn "Restarted: PostgresDb is running";
			else
				warn "PostgresDB is already running.";
			fi
		else
			if [[ ! -z $FORCE_INSTALL ]]; then
				if [[ -d /var/lib/pgsql/data ]]; then
					warn "Postgres DB exists. Removing all data.";
					/usr/bin/rm -rf /var/lib/pgsql/data >> /dev/null 2>&1;
				fi
			fi
			warn "Installing package: postgresql-server";
			yum install -y postgresql-server || die "Error: could not install package postgresql-server.";
			useradd postgres >> /dev/null 2>&1;
			/usr/bin/chmod -R 777 /tmp >> /dev/null 2>&1;

			su postgres -c "initdb -D /var/lib/pgsql/data" || die "Error: could not initialize postgress db.\
			Run ./configure -f to force re-install.";
			
			allowTCP="host    all             all             0.0.0.0/0            trust";
			grep -qxF "${allowTCP}" /var/lib/pgsql/data/pg_hba.conf || \
			echo "${allowTCP}" | tee -a /var/lib/pgsql/data/pg_hba.conf > /dev/null 2>&1;

			listenOnAll="listen_addresses='*'";
			grep -qxF "${listenOnAll}" /var/lib/pgsql/data/postgresql.conf || \
			echo "${listenOnAll}" | tee -a /var/lib/pgsql/data/postgresql.conf > /dev/null 2>&1;

			/usr/bin/chown -R postgres /var/lib/pgsql/data || die "Error: could not chown to postgres user.";

			systemctl restart postgresql.service || die "Error: could not start postgress service.";
			systemctl reload postgresql.service || die "Error: could not reload postgress service.";

			warn "PostgresDb installed and is running";
		fi

	} 1>>$INSTALL_LOGPATH 2> >(tee -a $INSTALL_LOGPATH >&2)

}

httpd_setup()
{
	{
		if [ -z $FORCE_INSTALL ] && [ -d "/var/www/html/xcp" ] && [ -f "/etc/httpd/conf.d/000-xcp.conf" ]; then
			systemctl is-active --quiet httpd;
			if [[ $? -gt 0 ]]; then # is-active ret 0 for active >=1 for inactive
				warn "Httpd server is configured but is not running. Restarting httpd service"
				systemctl restart httpd || die "Error: could not start Httpd service.";
				warn "Restarted: Httpd server is running"
			else
				warn "Httpd server is configured and already running."
			fi
		else
			if [[ ! -z $FORCE_INSTALL ]]; then
				if [ -d "/var/www/html/xcp" ]; then
					warn "XCP server files exist, Removing all data."
					/usr/bin/rm -rf /var/www/html/xcp
					/usr/bin/rm -f /etc/httpd/conf.d/000-xcp.conf
				fi
			fi
			warn "Installing package: httpd mod_ssl"
			yum install -y httpd mod_ssl || die "Error: could not install package httpd.";
			useradd apache 2>&1 > /dev/null;

			openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
			-keyout $SSLPVTKEYPATH \
			-out $SSLCERTPATH \
			-subj "/C=XX/ST=X/L=X/O=Netapp/OU=XCP/CN=$HOST_IP" >> /dev/null 2>&1 || \
			die "could not create self-signed certificate";

			/usr/bin/cp -rf ./xcp_gui/xcp /var/www/html || die "Failed to copy xcp gui files to /var/www/html";
			/usr/bin/chown -R apache /var/www/html/xcp || die "could not chown to user apache on /var/www/html/xcp";
			/usr/bin/cp -f ./xcp_gui/000-xcp.conf /etc/httpd/conf.d/ || \
			die "Failed to copy 000-xcp.conf to /etc/httpd/conf.d/";

			systemctl restart httpd || die "Could not restart httpd";
			warn "Httpd installed and server is running"
		fi
	} 1>>$INSTALL_LOGPATH 2> >(tee -a $INSTALL_LOGPATH >&2)

}

xcp_service()
{
	pkill -f "/usr/bin/xcp --listen"
	/usr/bin/cp -f ./linux/xcp /usr/bin/xcp || die "Could not copy xcp binary to /usr/bin path."
	/usr/bin/rm -f /lib/systemd/system/xcp.service >> /dev/null 2>&1

	echo "
[Unit]
Description=XCP systemd service.
After=httpd.service

[Service]
Type=simple
ExecStart=/bin/bash -ce \"exec /usr/bin/xcp --listen >> /opt/NetApp/xFiles/xcp/xcpfalogs/xcp_console.log 2>&1\"

[Install]
WantedBy=multi-user.target
" >>/lib/systemd/system/xcp.service || die "Could not create xcp.service in /lib/systemd/system path."

	systemctl daemon-reload || die "Could reload systemctl."
	systemctl restart xcp || die "could not start xcp service. Please check systemctl status -l xcp for more details."
	warn "XCP service started"
}

xcp_activate()
{
	if [ ! -e /opt/NetApp/xFiles/xcp/license ]; then
		# dummy run only to create the /opt/NetApp dirs
		./linux/xcp activate >> /dev/null 2>&1
		warn "# XCP license not found. "
		warn "# Download license file from https://xcp.netapp.com/"
		warn "# and copy to /opt/NetApp/xFiles/xcp/license"
		die "# Exiting!"
  	else
		warn "# Activating XCP license"
		./linux/xcp activate
	fi
}

main()
{
	umount -l /tmp >> /dev/null 2>&1
	about
	xcp_activate
	postgress_setup
	httpd_setup
	extra_pkg_installs
	xcp_service
	printf "$GREEN\nYou can now access XCP File Analytics using (admin:admin)"
	printf "$GREEN\nhttps://$HOST_IP/xcp \n$NC"

}

main

