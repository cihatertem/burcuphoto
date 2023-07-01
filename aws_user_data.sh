#!/bin/bash
apt update && apt upgrade -y && snap refresh
apt install -y docker.io docker-compose docker nfs-kernel-server nfs-common
apt autopurge -y
apt clean -y
ufw enable
ufw allow ssh
ufw allow http
ufw allow https
ufw allow from CHANGE_WITH_SWARM_SUBNET proto esp
ufw allow from CHANGE_WITH_SWARM_SUBNET proto udp to any port 4789
ufw allow from CHANGE_WITH_SWARM_SUBNET proto udp to any port 7946
ufw allow from CHANGE_WITH_SWARM_SUBNET proto tcp to any port 7946
ufw reload
usermod -aG docker ubuntu
docker swarm join --token CHANGE_WITH_SWARM_WORKER_TOKERN CHANGE_WITH_MANGER_IP:2377
echo "vm.swappiness = 1" >> /etc/sysctl.conf
echo "vm.vfs_cache_pressure = 50" >> /etc/sysctl.conf
echo "net.ipv4.conf.default.rp_filter=1" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.rp_filter=1" >> /etc/sysctl.conf
echo "net.ipv4.tcp_syncookies=1" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 2048" >> /etc/sysctl.conf
echo "net.ipv4.tcp_synack_retries = 2" >> /etc/sysctl.conf
echo "net.ipv4.tcp_syn_retries = 5" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.accept_source_route = 0" >> /etc/sysctl.conf
echo "net.ipv6.conf.all.accept_source_route = 0" >> /etc/sysctl.conf
echo "net.ipv4.conf.default.accept_source_route = 0" >> /etc/sysctl.conf
echo "net.ipv6.conf.default.accept_source_route = 0" >> /etc/sysctl.conf
echo "net.ipv4.ip_local_port_range = 1024 65535" >> /etc/sysctl.conf
echo "fs.file-max = 2097152" >> /etc/sysctl.conf
echo "fs.suid_dumpable = 0" >> /etc/sysctl.conf
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.core.netdev_max_backlog = 262144" >> /etc/sysctl.conf
echo "net.core.optmem_max = 25165824" >> /etc/sysctl.conf
echo "net.core.rmem_default = 31457280" >> /etc/sysctl.conf
echo "net.core.rmem_max = 67108864" >> /etc/sysctl.conf
echo "net.core.wmem_default = 31457280" >> /etc/sysctl.conf
echo "net.core.wmem_max = 67108864" >> /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control = bbr" >> /etc/sysctl.conf
echo "net.core.default_qdisc = fq" >> /etc/sysctl.conf
modprobe tcp_bbr
echo "tcp_bbr" > /etc/modules-load.d/bbr.conf
echo "*       soft    nofile      999999" >> /etc/security/limits.conf
echo "*       hard    nofile      999999" >> /etc/security/limits.conf
echo "root    soft    nofile      999999" >> /etc/security/limits.conf
echo "root    hard    nofile      999999" >> /etc/security/limits.conf
echo "session required        pam_limits.so" >> /etc/pam.d/common-session
echo "session required        pam_limits.so" >> /etc/pam.d/common-session-noninteractive
sysctl -p
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults  0 0" >> /etc/fstab
echo "none /run/shm tmpfs defaults,ro 0 0" >> /etc/fstab
hostnamectl set-hostname CHANGE_WITH_WORKER_HOSTNAME
timedatectl set-timezone Europe/Istanbul
shutdown now -r