#!/usr/bin/env python3
"""查询 DeepSeek 账户余额（不打印 API Key）。用法: python scripts/check_deepseek_balance.py"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
BASE = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")

if not KEY:
    print("DEEPSEEK_API_KEY not set in .env")
    sys.exit(1)

r = requests.get(
    f"{BASE}/user/balance",
    headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json"},
    timeout=30,
)
print("HTTP", r.status_code)
try:
    data = r.json()
except Exception:
    print(r.text[:500])
    sys.exit(1)

print(json.dumps(data, indent=2, ensure_ascii=False))
print()
print("说明：DeepSeek 官方 API 仅返回账户余额，不返回历史 token 用量。")
print("单次报告约 9–10 次请求（银卡九页 / 金钻加流年）；排盘不消耗 token。")
print("详细用量请在 https://platform.deepseek.com 控制台导出。")
