#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import pwd
import json
import string
import syslog
import random
import hashlib
import httplib
import datetime
import platform
import socket


def auth_log(msg):
    syslog.openlog(facility=syslog.LOG_AUTH)
    syslog.syslog("MultiFactors Authentication: " + msg)
    syslog.closelog()


def action_tg(content):
    host = "tgapi.xxx.workers.dev"
    headers = {'Content-Type': 'application/json'}
    send_url = '/'
    data = {"text": content}

    try:
        httpClient = httplib.HTTPSConnection(host, timeout=10)
        httpClient.request("POST", send_url, json.dumps(data), headers=headers)
        response = httpClient.getresponse()
        result = json.loads(response.read())
        if result['ok'] != True:
            auth_log('Failed to send verification code using tg: %s' % result)
            return False
    except Exception as e:
        auth_log('Error sending verification code using tg: %s' % e)
        return False
    finally:
        if httpClient:
            httpClient.close()

    auth_log('Send verification code using tg successfully.')
    return True


def get_user_comment(user):
    try:
        comments = pwd.getpwnam(user).pw_gecos
    except:
        auth_log("No local user (%s) found." % user)
        comments = ''

    return comments


def get_hash(plain_text):
    key_hash = hashlib.sha512()
    key_hash.update(plain_text)

    return key_hash.digest()


def gen_key(pamh, user, length):
    pin = ''.join(random.choice(string.digits) for i in range(length))
    hostname = platform.node().split('.')[0]
    hostip = socket.gethostbyname(platform.node())
    content = "[MFA] %s 使用 %s 正在登录 %s(%s), 验证码为【%s】, 1分钟内有效。" % (pamh.rhost, user, hostname, str(hostip), pin)
    auth_log(content)
    result = action_tg(content)

    pin_time = datetime.datetime.now()
    return get_hash(pin), pin_time


def pam_sm_authenticate(pamh, flags, argv):
    PIN_LENGTH = 6  # PIN码长度
    PIN_LIVE = 60  # PIN存活时间,超出时间验证失败
    PIN_LIMIT = 3  # 限制错误尝试次数
    EMERGENCY_HASH = "\xef\x8d\xd0\x1ahZ5'\x19>I8\xe3\x92\x80!C\x8a\x01\xe7\xcc\xc8\x89\n\xc3\x02\xd8q\xd0f\xf1\xb2!D\xaa\x8f{\xe9\\'\xa1N\xd6\x84$q\x87\xe1\xe4\x16\x0e\x9c\xce\xa8&\x8a\xf0\x852\xf6B\x7fS\x12"  # 预定义验证码123456的hash

    try:
        user = pamh.get_user()
    except pamh.exception as e:
        return e.pam_result

    auth_log("login_ip: %s, login_user: %s" % (pamh.rhost, user))

    if get_user_comment(user) == '':
        msg = pamh.Message(pamh.PAM_ERROR_MSG,
                           "[Warning] You need to set the  username in the comment block for user %s." % (
                               user))
        pamh.conversation(msg)
        return pamh.PAM_ABORT

    pin, pin_time = gen_key(pamh, user, PIN_LENGTH)

    for attempt in range(0, PIN_LIMIT):  # 限制错误尝试次数
        msg = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, "Verification code:")
        resp = pamh.conversation(msg)
        resp_time = datetime.datetime.now()
        input_interval = resp_time - pin_time
        if input_interval.seconds > PIN_LIVE:
            msg = pamh.Message(pamh.PAM_ERROR_MSG, "[Warning] Time limit exceeded.")
            pamh.conversation(msg)
            return pamh.PAM_ABORT
        resp_hash = get_hash(resp.resp)
        if resp_hash == pin or resp_hash == EMERGENCY_HASH:  # 用户输入与生成的验证码进行校验
            return pamh.PAM_SUCCESS
        else:
            continue

    msg = pamh.Message(pamh.PAM_ERROR_MSG, "[Warning] Too many authentication failures.")
    pamh.conversation(msg)
    return pamh.PAM_AUTH_ERR


def pam_sm_setcred(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_acct_mgmt(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_open_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_close_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_chauthtok(pamh, flags, argv):
    return pamh.PAM_SUCCESS
