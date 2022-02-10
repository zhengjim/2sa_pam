#!/bin/bash

echo "Start install ..."
yum -y install gcc make pam pam-devel python-devel
tar zxf pam-python-1.0.7.tar.gz
cd pam-python-1.0.7/src
make pam_python.so
if [ ! -f pam_python.so ]; then
  echo "Error: compile pam_python.so fail!"
  exit 1
fi
cp pam_python.so /usr/lib64/security/
cd $(dirname $(dirname "$PWD"))
cp pam_notice_auth.py /usr/lib64/security/pam_notice_auth.py
chmod +x /usr/lib64/security/pam_notice_auth.py
sed -i 's#^ChallengeResponseAuthentication no#ChallengeResponseAuthentication yes#' /etc/ssh/sshd_config
echo 'auth requisite pam_python.so /usr/lib64/security/pam_notice_auth.py' >> /etc/pam.d/sshd
systemctl restart sshd

echo "installation is complete..."