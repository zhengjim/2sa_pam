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


class Config:
    """ 配置 """
    EMERGENCY_HASH = "admin"  # 预定义万能验证码,务必修改！
    PIN_LENGTH = 6  # PIN码长度
    PIN_LIVE = 60  # PIN存活时间,超出时间验证失败
    PIN_LIMIT = 3  # 限制错误尝试次数

    # tg通知
    open_tg = False  # 是否开启
    tg_token = "xxx:xxx"  # tg token
    tg_chat_id = "xxxx"  # chai_id 发送人id

    # 钉钉通知
    open_dingding = True  # 是否开启
    dingding_token = "xxxxxxxx"  # dingding token


def auth_log(msg):
    """记录日志

    :param msg: 消息
    :return:
    """
    syslog.openlog(facility=syslog.LOG_AUTH)
    syslog.syslog("MultiFactors Authentication: " + msg)
    syslog.closelog()


def action_tg(content):
    host = "api.telegram.org"
    send_url = "/bot%s/sendMessage" % Config.tg_token
    headers = {'Content-Type': 'application/json'}
    data = {"chat_id": Config.tg_chat_id, "text": content}
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


def action_dingding(content):
    host = "oapi.dingtalk.com"
    send_url = "/robot/send?access_token=%s" % Config.dingding_token
    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "text",
        "text": {"content": content},
        "isAtAll": True
    }
    try:
        httpClient = httplib.HTTPSConnection(host, timeout=10)
        httpClient.request("POST", send_url, json.dumps(data), headers=headers)
        response = httpClient.getresponse()
        result = json.loads(response.read())
        if result['errmsg'] != "ok":
            auth_log('Failed to send verification code using dingding: %s' % result)
            return False
    except Exception as e:
        auth_log('Error sending verification code using dingding: %s' % e)
        return False
    finally:
        if httpClient:
            httpClient.close()

    auth_log('Send verification code using dingding successfully.')
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
    if Config.open_tg:
        action_tg(content)
    if Config.open_dingding:
        action_dingding(content)

    pin_time = datetime.datetime.now()
    return get_hash(pin), pin_time


def pam_sm_authenticate(pamh, flags, argv):
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

    pin, pin_time = gen_key(pamh, user, Config.PIN_LENGTH)

    for attempt in range(0, Config.PIN_LIMIT):  # 限制错误尝试次数
        msg = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, "Verification code:")
        resp = pamh.conversation(msg)
        resp_time = datetime.datetime.now()
        input_interval = resp_time - pin_time
        if input_interval.seconds > Config.PIN_LIVE:
            msg = pamh.Message(pamh.PAM_ERROR_MSG, "[Warning] Time limit exceeded.")
            pamh.conversation(msg)
            return pamh.PAM_ABORT
        resp_hash = get_hash(resp.resp)
        if resp_hash == pin or resp_hash == get_hash(Config.EMERGENCY_HASH):  # 用户输入与生成的验证码进行校验
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
