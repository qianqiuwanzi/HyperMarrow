"""
HyperMarrow 用户认证模块
阿里云短信验证码（与 commercial/license_server/sms.py 一致）
"""
import random
import time
import os
import json
from datetime import datetime, timedelta
from typing import Optional

# 验证码存储：phone → {code, expires_at, attempts, sent_at}
_code_store: dict[str, dict] = {}
# 用户存储：phone → user_info
_user_store: dict[str, dict] = {}

CODE_EXPIRE_SECONDS = 300   # 5分钟有效
CODE_COOLDOWN_SECONDS = 60  # 同一手机号60秒内不可重复发送
MAX_CODE_ATTEMPTS = 5


def _sms_configured() -> bool:
    """检查阿里云短信是否已配置"""
    return bool(os.environ.get("SMS_ACCESS_KEY_ID") and os.environ.get("SMS_ACCESS_KEY_SECRET"))


def _send_sms_aliyun(phone: str, code: str) -> dict:
    """通过阿里云短信 SDK 发送验证码"""
    try:
        from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
        from alibabacloud_tea_openapi import models as open_api_models

        config = open_api_models.Config(
            access_key_id=os.environ["SMS_ACCESS_KEY_ID"],
            access_key_secret=os.environ["SMS_ACCESS_KEY_SECRET"],
        )
        config.endpoint = "dysmsapi.aliyuncs.com"
        client = DysmsapiClient(config)

        req = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=os.environ.get("SMS_SIGN_NAME", "千视科技深圳有限公司"),
            template_code=os.environ.get("SMS_TEMPLATE_CODE", "SMS_336450079"),
            template_param=json.dumps({"code": code}),
        )
        resp = client.send_sms(req)

        if resp.body.code == "OK":
            print(f"[SMS] 验证码已发送至 {phone}", flush=True)
            return {"success": True, "message": "验证码已发送"}
        else:
            err = resp.body.message or resp.body.code
            print(f"[SMS] 发送失败: {err}", flush=True)
            return {"success": False, "message": f"短信发送失败: {err}"}

    except Exception as e:
        print(f"[SMS] 异常: {e}", flush=True)
        return {"success": False, "message": f"短信服务异常: {e}"}


def generate_code(phone: str) -> tuple[str, Optional[str]]:
    """生成6位验证码并发送。返回 (code, dev_code_or_None)"""
    # 冷却检查
    entry = _code_store.get(phone)
    if entry and time.time() - entry.get("sent_at", 0) < CODE_COOLDOWN_SECONDS:
        raise ValueError("验证码已发送，请60秒后重试")

    code = str(random.randint(100000, 999999))
    _code_store[phone] = {
        "code": code,
        "expires_at": time.time() + CODE_EXPIRE_SECONDS,
        "attempts": 0,
        "sent_at": time.time(),
    }

    if _sms_configured():
        # 真实短信发送
        result = _send_sms_aliyun(phone, code)
        if result["success"]:
            return code, None  # 生产模式：不泄露验证码
        else:
            raise RuntimeError(result["message"])
    else:
        # 开发模式：打印到控制台并返回验证码
        print(f"\n{'='*60}")
        print(f"  📱 验证码 [{phone}]: {code}")
        print(f"  ⏰ 有效期: {CODE_EXPIRE_SECONDS // 60} 分钟")
        print(f"  💡 设置 SMS_ACCESS_KEY_ID + SMS_ACCESS_KEY_SECRET 启用真实短信")
        print(f"{'='*60}\n")
        return code, code


def verify_code(phone: str, code: str) -> dict:
    """验证验证码"""
    entry = _code_store.get(phone)

    if not entry:
        return {"success": False, "message": "请先获取验证码"}

    if time.time() > entry["expires_at"]:
        del _code_store[phone]
        return {"success": False, "message": "验证码已过期，请重新获取"}

    if entry["attempts"] >= MAX_CODE_ATTEMPTS:
        del _code_store[phone]
        return {"success": False, "message": "验证码尝试次数过多，请重新获取"}

    entry["attempts"] += 1

    if entry["code"] != code:
        remaining = MAX_CODE_ATTEMPTS - entry["attempts"]
        return {"success": False, "message": f"验证码错误，剩余尝试次数: {remaining}"}

    # 验证成功
    del _code_store[phone]

    # 获取或创建用户
    user = _user_store.get(phone)
    if not user:
        user_id = f"u{int(time.time())}{random.randint(100, 999)}"
        user = {
            "id": user_id,
            "phone": phone,
            "display_name": f"用户{phone[-4:]}",
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
        }
        _user_store[phone] = user
    else:
        user["last_login"] = datetime.now().isoformat()

    return {
        "success": True,
        "message": "登录成功",
        "user": user,
        "token": f"hm_{user['id']}_{int(time.time())}",
        "expires_in": 86400,
    }


def get_user_by_token(token: str) -> dict | None:
    """根据 token 查找用户"""
    if not token or not token.startswith("hm_"):
        return None
    try:
        parts = token.split("_")
        if len(parts) < 3:
            return None
        user_id = parts[1]
        for user in _user_store.values():
            if user["id"] == user_id:
                return user
    except Exception:
        pass
    return None
