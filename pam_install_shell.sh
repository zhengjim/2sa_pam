#!/bin/bash

echo "start install ..."
yum -y install gcc make pam pam-devel python-devel
wget -O pam-python-1.0.7.tar.gz https://sourceforge.net/projects/pam-python/files/pam-python-1.0.7-1/pam-python-1.0.7.tar.gz/download --no-check-certificate
tar zxf pam-python-1.0.7.tar.gz
cd pam-python-1.0.7/src
sed -i '43d' pam_python.c
sed -i  "30a #include <Python.h>" pam_python.c
make pam_python.so
if [ ! -f pam_python.so ]; then
  echo "Error: compile pam_python.so fail!"
  exit 1
fi
cp pam_python.so /usr/lib64/security/
cd $(dirname $(dirname "$PWD"))
cp pam_tg_auth.py /usr/lib64/security/pam_tg_auth.py
chmod +x /usr/lib64/security/pam_tg_auth.py
sed -i 's#^ChallengeResponseAuthentication no#ChallengeResponseAuthentication yes#' /etc/ssh/sshd_config
echo 'auth requisite pam_python.so /usr/lib64/security/pam_tg_auth.py' >> /etc/pam.d/sshd
systemctl restart sshd

echo "ok"