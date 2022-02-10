#!/bin/bash

echo "Start uninstall ..."

sed -i 's#^ChallengeResponseAuthentication yes#ChallengeResponseAuthentication no#' /etc/ssh/sshd_config
sed -i '/pam_notice_auth/d' /etc/pam.d/sshd
rm -rf /usr/lib64/security/pam_python.so
rm -rf /usr/lib64/security/pam_auth.py
rm -rf pam-python-1.0.7
systemctl restart sshd

echo "Uninstall complete ..."