"""
八页报告生成器 - 分页调用 DeepSeek，避免 max_tokens 截断导致「只显示一半」
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

import requests


class ReportGenerator:
    """生成命理报告（按页/批次请求，保证内容完整）"""

    PAGE_SPECS = [
        ("page1", "八字命盘与基本信息", "四柱、十神、五行旺衰、大运走势、知进退建议"),
        ("page2", "事业流年详批 (Part 1)", "当年事业运势、大事、注意事项、关键月份"),
        ("page3", "事业流年详批 (Part 2)", "事业特质、五行行业方向、职业与发展策略"),
        ("page4", "财运流年详批 (Part 1)", "财运趋势、投资适否、旺财破财月份与方向"),
        ("page5", "财运流年详批 (Part 2)", "资产五行方向、理财方式、风险与积累策略"),
        ("page6", "感情流年详批 (Part 1)", "感情事件预测、桃花、注意事项"),
        ("page7", "感情流年详批 (Part 2)", "风水布局、另一半特质、感情时机"),
        ("page8", "健康流年详批", "健康风险、易病月份、五脏对应、就医建议"),
        ("page9", "流年预测专章", "流年刑冲合害、旺防月、四大领域评分与开运建议"),
    ]

    def __init__(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, bazi_data, birth_info, payment_tier="silver"):
        include_liunian = payment_tier in ("gold", "diamond")
        pages = self.PAGE_SPECS if include_liunian else self.PAGE_SPECS[:8]
        context = self._bazi_context(bazi_data, birth_info)

        report: Dict = {}
        # 每次 2 页，避免截断
        for i in range(0, len(pages), 2):
            batch = pages[i : i + 2]
            chunk = self._generate_batch(context, batch)
            report.update(chunk)

        for key, title, _ in pages:
            if key not in report or not str(report[key].get("content", "")).strip():
                report[key] = {
                    "title": title,
                    "content": f"（{title}生成不完整，请重试生成报告）",
                }
        return report

    def _bazi_context(self, bazi_data, birth_info) -> str:
        bazi = bazi_data["bazi"]
        da_yun = bazi_data.get("da_yun") or []
        liu_nian = bazi_data.get("liu_nian") or []
        current_da_yun = da_yun[0] if da_yun else None
        current_liu_nian = next(
            (n for n in liu_nian if n.get("is_current")),
            liu_nian[-1] if liu_nian else None,
        )
        dy = (
            f"第{current_da_yun['step']}步 {current_da_yun['gan']}{current_da_yun['zhi']} {current_da_yun['years']}"
            if current_da_yun
            else "未知"
        )
        ln = (
            f"{current_liu_nian['year']}年 {current_liu_nian['gan']}{current_liu_nian['zhi']}"
            if current_liu_nian
            else "未知"
        )
        return (
            f"姓名：{birth_info.get('name', '用户')}；性别：{bazi_data.get('gender')}；"
            f"出生：{birth_info.get('birth_date', '')}；"
            f"八字：年{bazi['年柱'][0]}{bazi['年柱'][1]} "
            f"月{bazi['月柱'][0]}{bazi['月柱'][1]} "
            f"日{bazi['日柱'][0]}{bazi['日柱'][1]} "
            f"时{bazi['时柱'][0]}{bazi['时柱'][1]}；"
            f"日主：{bazi_data.get('day_master')}；"
            f"五行：{json.dumps(bazi_data.get('wuxing_stats', {}), ensure_ascii=False)}；"
            f"当前大运：{dy}；当前流年：{ln}。"
            "分析须结合流年干支与命局作用，给出可操作建议。"
        )

    def _generate_batch(self, context: str, batch: List) -> Dict:
        keys = [b[0] for b in batch]
        specs = "\n".join(f"- {k}: 《{title}》— {focus}" for k, title, focus in batch)
        prompt = f"""根据命盘写详细命理报告（仅输出 JSON，不要 markdown）。

命盘：{context}

请生成以下页面（每页 content 至少 350 汉字，写完整段落）：
{specs}

输出格式示例：
{{"{keys[0]}": {{"title": "...", "content": "完整正文..."}}{''.join([f', "{k}": {{"title": "...", "content": "..."}}' for k in keys[1:]])}}}
"""
        raw = self._call_deepseek(prompt)
        parsed = self._parse_json_loose(raw)
        out = {}
        for key, title, _ in batch:
            item = parsed.get(key) if isinstance(parsed, dict) else None
            if isinstance(item, dict):
                content = str(item.get("content") or "").strip()
                out[key] = {
                    "title": item.get("title") or title,
                    "content": content or f"（{title}内容为空，请重试）",
                }
            elif isinstance(item, str) and item.strip():
                out[key] = {"title": title, "content": item.strip()}
            else:
                # 若整段解析失败，尝试把原文塞进第一页
                out[key] = {
                    "title": title,
                    "content": (raw[:1200] if key == keys[0] and raw else f"（{title}生成失败，请重试）"),
                }
        return out

    def _call_deepseek(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是专业八字命理师。只输出合法 JSON 对象，不要代码块标记。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.6,
            "max_tokens": 8192,
        }
        url = f"{self.base_url}/v1/chat/completions"
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code != 200:
            raise Exception(f"DeepSeek API错误: {response.status_code} - {response.text[:500]}")
        return response.json()["choices"][0]["message"]["content"]

    def _parse_json_loose(self, text: str) -> dict:
        if not text:
            return {}
        cleaned = text.strip()
        if "```json" in cleaned:
            start = cleaned.find("```json") + 7
            end = cleaned.find("```", start)
            cleaned = cleaned[start:end].strip() if end > start else cleaned[start:].strip()
        elif cleaned.startswith("```"):
            start = cleaned.find("```") + 3
            end = cleaned.find("```", start)
            cleaned = cleaned[start:end].strip() if end > start else cleaned[start:].strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 截断 JSON：尝试补全常见结尾
        for candidate in (cleaned, cleaned + '"}', cleaned + '"}}', cleaned + "}}"):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {}
