"""
八页报告生成器 - 分页调用 DeepSeek；专业段与白话段分字段，强制分段排版
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

import requests


class ReportGenerator:
    """生成命理报告（按页/批次请求，保证内容完整、分段可读）"""

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

    FORBIDDEN_PLAIN = (
        "十神、正官、七杀、食神、伤官、正印、偏印、比肩、劫财、正财、偏财、"
        "刑冲合害、干支、天干、地支、藏干、大运、流年、流月、神煞、旺衰、通根、调候、格局、用神、忌神"
    )

    def __init__(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, bazi_data, birth_info, payment_tier="silver"):
        include_liunian = payment_tier in ("gold", "diamond")
        pages = self.PAGE_SPECS if include_liunian else self.PAGE_SPECS[:8]
        context = self._bazi_context(bazi_data, birth_info)

        report: Dict = {}
        # 每次 1 页，内容更深、分段更稳
        for spec in pages:
            chunk = self._generate_batch(context, [spec])
            report.update(chunk)

        for key, title, _ in pages:
            if key not in report or not self._page_has_text(report[key]):
                report[key] = {
                    "title": title,
                    "professional": [f"（{title}生成不完整，请重试生成报告）"],
                    "plain": {
                        "summary": "本页生成失败，请重新生成报告。",
                        "points": [],
                        "detail": "",
                    },
                    "content": f"（{title}生成不完整，请重试生成报告）",
                }
        return report

    @staticmethod
    def _page_has_text(page: Any) -> bool:
        if not isinstance(page, dict):
            return False
        if str(page.get("content") or "").strip():
            return True
        pro = page.get("professional")
        if isinstance(pro, list) and any(str(x).strip() for x in pro):
            return True
        if isinstance(pro, str) and pro.strip():
            return True
        plain = page.get("plain")
        if isinstance(plain, dict) and (
            str(plain.get("summary") or "").strip()
            or str(plain.get("detail") or "").strip()
            or plain.get("points")
        ):
            return True
        return False

    def _bazi_context(self, bazi_data, birth_info) -> str:
        bazi = bazi_data["bazi"]
        da_yun = bazi_data.get("da_yun") or []
        liu_nian = bazi_data.get("liu_nian") or []
        current_da_yun = next((d for d in da_yun if d.get("is_current")), da_yun[0] if da_yun else None)
        current_liu_nian = next(
            (n for n in liu_nian if n.get("is_current")),
            liu_nian[-1] if liu_nian else None,
        )
        dy = (
            f"第{current_da_yun.get('step')}步 {current_da_yun.get('gan')}{current_da_yun.get('zhi')} "
            f"{current_da_yun.get('years', '')}"
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
        )

    def _generate_batch(self, context: str, batch: List) -> Dict:
        keys = [b[0] for b in batch]
        specs = "\n".join(f"- {k}: 《{title}》主题：{focus}" for k, title, focus in batch)
        key0 = keys[0]
        prompt = f"""根据命盘写命理报告。只输出合法 JSON，不要 markdown 代码块。

命盘：{context}

要生成的页：
{specs}

【输出结构·强制】每一页必须是对象，字段如下（不要用单一 content 长文本堆在一起）：
"{key0}": {{
  "title": "页面标题",
  "professional": [
    "第一段：本页核心判断（约60-90字，独立完整句）",
    "第二段：展开分析细节（约60-90字）",
    "第三段：月份或阶段要点（约60-90字）",
    "第四段：风险与应对（约60-90字）"
  ],
  "plain": {{
    "summary": "一句人话总结（不超过40字，零术语）",
    "points": [
      "可执行建议1（短句）",
      "可执行建议2",
      "可执行建议3"
    ],
    "detail": "再用一段白话解释（80-120字，像朋友聊天，零术语）"
  }}
}}

硬性要求：
1) professional 必须是数组，恰好 4 个字符串，每条是独立段落，禁止把全文塞进一个字符串。
2) plain.points 必须是 3 条短建议。
3) plain 全文禁止出现：{self.FORBIDDEN_PLAIN}
4) 专业段可用术语；白话段绝对零术语。
5) 若有多页，每个 page key 都按同一结构输出。
"""
        raw = self._call_deepseek(prompt)
        parsed = self._parse_json_loose(raw)
        # 模型有时不包 page key，整段就是一页
        if isinstance(parsed, dict) and key0 not in parsed:
            if "professional" in parsed or "plain" in parsed or "content" in parsed:
                parsed = {key0: parsed}
        out: Dict[str, Any] = {}
        for key, title, _ in batch:
            item = parsed.get(key) if isinstance(parsed, dict) else None
            page = self._coerce_page(item, title, raw if key == keys[0] else "")
            page = self._ensure_plain_section(page, title)
            out[key] = page
        return out

    def _plain_missing(self, plain: Any) -> bool:
        if not isinstance(plain, dict):
            return True
        summary = str(plain.get("summary") or "").strip()
        detail = str(plain.get("detail") or "").strip()
        points = plain.get("points") or []
        if any(x in summary for x in ("请重试", "见上方专业解读", "不完整", "生成失败")):
            return True
        if len(summary) < 6 and len(detail) < 20 and not points:
            return True
        return False

    def _ensure_plain_section(self, page: Dict[str, Any], title: str) -> Dict[str, Any]:
        """白话缺失时单独再请求一次，保证绿框一定有内容。"""
        plain = page.get("plain") if isinstance(page.get("plain"), dict) else {}
        if not self._plain_missing(plain):
            page["content"] = ReportGenerator.build_content_markdown(page)
            return page

        pro_list = [str(p).strip() for p in (page.get("professional") or []) if str(p).strip()]
        pro_text = "\n".join(pro_list)
        if not pro_text or pro_text.startswith("（"):
            page["plain"] = {
                "summary": "这页内容暂时不完整。",
                "points": ["请点击重新生成完整报告。", "生成后再查看白话说明。", "也可先看上方专业解读作参考。"],
                "detail": "系统未能写出白话段落，重试生成通常可以一次修好。",
            }
            page["content"] = ReportGenerator.build_content_markdown(page)
            return page

        prompt = f"""你是翻译成大白话的助手。阅读下面「{title}」的专业命理解读，改写成普通人能懂的话。
只输出 JSON 对象（不要代码块），格式严格为：
{{"summary":"一句人话总结，不超过40字","points":["建议1","建议2","建议3"],"detail":"80到120字的白话解释，像朋友聊天"}}

严禁出现这些词：{self.FORBIDDEN_PLAIN}
不要提八字术语，只说工作/钱/感情/健康/人际/时机/注意什么。

专业原文：
{pro_text[:1800]}
"""
        try:
            raw = self._call_deepseek(prompt)
            parsed = self._parse_json_loose(raw)
            if not isinstance(parsed, dict):
                parsed = {}
            # 兼容包了一层
            if "plain" in parsed and isinstance(parsed["plain"], dict):
                parsed = parsed["plain"]
            pts = parsed.get("points") or []
            if isinstance(pts, str):
                pts = [p.strip() for p in re.split(r"[；;\n]+", pts) if p.strip()]
            filled = {
                "summary": str(parsed.get("summary") or "").strip(),
                "points": [str(p).strip() for p in pts if str(p).strip()][:5],
                "detail": str(parsed.get("detail") or "").strip(),
            }
            if self._plain_missing(filled):
                # 最后兜底：从专业段抽第一句做人话摘要壳
                first = re.split(r"[。！？]", pro_text)[0].strip()
                filled = {
                    "summary": (first[:36] + "…") if len(first) > 36 else (first or "先看这几条建议"),
                    "points": [
                        "先做一件最要紧、且短期内能完成的事。",
                        "少同时开太多新计划，把精力放在一两件上。",
                        "有不确定的决定，先缓冲几天再拍板。",
                    ],
                    "detail": (
                        "上面的术语可以先跳过。简单说：这段话提醒你留意节奏和选择，"
                        "别急着硬推；把重要事务排清楚，并给自己留一点调整空间。"
                    ),
                }
            page["plain"] = filled
        except Exception as e:
            print(f"ensure_plain_section error: {e}")
            page["plain"] = {
                "summary": "先抓住「稳一点、清楚一点」就够了",
                "points": [
                    "重要决定不要当天硬推。",
                    "优先处理最影响收入或关系的一件事。",
                    "身体与心情不对时，先减负再冲刺。",
                ],
                "detail": "白话段自动补写时遇到问题，但不影响上方专业内容。建议重新生成一次报告。",
            }
        page["content"] = ReportGenerator.build_content_markdown(page)
        return page

    def _coerce_page(self, item: Any, title: str, fallback_raw: str = "") -> Dict[str, Any]:
        if isinstance(item, str) and item.strip():
            page = ReportGenerator._split_legacy_content(item.strip(), title)
            return page
        if not isinstance(item, dict):
            msg = fallback_raw[:800] if fallback_raw else f"（{title}生成失败，请重试）"
            return {
                "title": title,
                "professional": [msg],
                "plain": {"summary": "", "points": [], "detail": ""},
                "content": msg,
            }

        # 兼容中文字段名
        if "professional" not in item and item.get("专业解读"):
            item = dict(item)
            item["professional"] = item.get("专业解读")
        if "plain" not in item:
            for alt in ("白话说明", "白话", "plain_text", "baihua"):
                if alt in item:
                    item = dict(item)
                    item["plain"] = item.get(alt)
                    break

        pro = item.get("professional")
        if isinstance(pro, str):
            paragraphs = ReportGenerator._split_paragraphs(pro)
        elif isinstance(pro, list):
            paragraphs = [str(x).strip() for x in pro if str(x).strip()]
        else:
            paragraphs = []

        plain_raw = item.get("plain")
        if isinstance(plain_raw, str):
            plain = {
                "summary": plain_raw.strip()[:80],
                "points": [],
                "detail": plain_raw.strip(),
            }
        elif isinstance(plain_raw, dict):
            pts = plain_raw.get("points") or plain_raw.get("建议") or plain_raw.get("怎么做") or []
            if isinstance(pts, str):
                pts = [p.strip() for p in re.split(r"[；;\n]+", pts) if p.strip()]
            plain = {
                "summary": str(
                    plain_raw.get("summary")
                    or plain_raw.get("一句话")
                    or plain_raw.get("总结")
                    or ""
                ).strip(),
                "points": [str(p).strip() for p in pts if str(p).strip()][:5],
                "detail": str(
                    plain_raw.get("detail")
                    or plain_raw.get("说明")
                    or plain_raw.get("解释")
                    or ""
                ).strip(),
            }
        else:
            plain = {"summary": "", "points": [], "detail": ""}

        # 兼容旧模型只返回 content
        if (not paragraphs or self._plain_missing(plain)) and item.get("content"):
            legacy = ReportGenerator._split_legacy_content(str(item.get("content")), title)
            if not paragraphs:
                paragraphs = legacy.get("professional") or []
            if self._plain_missing(plain):
                plain = legacy.get("plain") or plain

        if not paragraphs:
            paragraphs = [f"（{title}专业解读缺失）"]

        page = {
            "title": item.get("title") or item.get("标题") or title,
            "professional": paragraphs,
            "plain": plain,
        }
        page["content"] = ReportGenerator.build_content_markdown(page)
        return page

    @staticmethod
    def _split_legacy_content(text: str, title: str) -> Dict[str, Any]:
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        pro_part, plain_part = text, ""
        m = re.search(r"(#{1,6}\s*)?(白话说明|【白话说明】|\*\*白话说明\*\*)", text)
        if m:
            pro_part = text[: m.start()].strip()
            plain_part = text[m.end() :].strip()
        pro_part = re.sub(r"^(#{1,6}\s*)?(专业解读|【专业解读】|\*\*专业解读\*\*)\s*", "", pro_part).strip()
        pro_part = re.sub(r"^---+\s*", "", pro_part).strip()
        plain_part = re.sub(r"^[:：\s\*]+", "", plain_part).strip()
        plain_part = re.sub(r"^---+\s*", "", plain_part).strip()

        # 解析「一句话」「怎么做」markdown
        summary = ""
        detail_lines = []
        points = []
        for line in plain_part.split("\n"):
            raw_line = line.strip()
            if not raw_line:
                continue
            sm = re.match(r"^\*\*一句话[：:]*\*\*\s*(.+)$", raw_line)
            if not sm:
                sm = re.match(r"^一句话[：:]\s*(.+)$", raw_line)
            if sm:
                summary = sm.group(1).strip()
                continue
            if re.match(r"^\*\*怎么做\*\*", raw_line) or raw_line in ("怎么做", "怎么做："):
                continue
            if re.match(r"^([一二三四五六七八九十\d]+[\.、．]|[-•●*]|\d+\))\s*", raw_line):
                points.append(
                    re.sub(r"^([一二三四五六七八九十\d]+[\.、．]|[-•●*]|\d+\))\s*", "", raw_line)
                )
                continue
            detail_lines.append(raw_line)

        paragraphs = ReportGenerator._split_paragraphs(pro_part) or ([pro_part] if pro_part else [])
        detail = "\n".join(detail_lines).strip()
        if not summary and detail:
            summary = detail.split("\n")[0][:40]
        if not summary and not detail and not points:
            # 无白话标记：先留空，交由 _ensure_plain_section 补写
            summary, detail, points = "", "", []

        page = {
            "title": title,
            "professional": paragraphs or [f"（{title}）"],
            "plain": {
                "summary": summary,
                "points": points[:5],
                "detail": detail,
            },
        }
        page["content"] = ReportGenerator.build_content_markdown(page)
        return page

    @staticmethod
    def _split_paragraphs(text: str) -> List[str]:
        if not text:
            return []
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        # 双换行优先
        parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        if len(parts) >= 2:
            return parts
        # 单换行且行不太短
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) >= 3 and all(len(ln) >= 20 for ln in lines):
            return lines
        # 按句号切成约 3～4 段
        sentences = [s.strip() for s in re.split(r"(?<=[。！？；])", text) if s.strip()]
        if len(sentences) <= 1:
            return [text]
        chunk_size = max(1, (len(sentences) + 3) // 4)
        chunks = []
        for i in range(0, len(sentences), chunk_size):
            chunks.append("".join(sentences[i : i + chunk_size]).strip())
        return [c for c in chunks if c]

    @staticmethod
    def build_content_markdown(page: Dict[str, Any]) -> str:
        """供 PDF/导出：标准分段 Markdown。"""
        lines: List[str] = ["#### 专业解读", ""]
        for p in page.get("professional") or []:
            lines.append(str(p).strip())
            lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("#### 白话说明")
        lines.append("")
        plain = page.get("plain") or {}
        if isinstance(plain, dict):
            if plain.get("summary"):
                lines.append(f"**一句话：** {plain['summary']}")
                lines.append("")
            pts = plain.get("points") or []
            if pts:
                lines.append("**怎么做：**")
                lines.append("")
                for i, pt in enumerate(pts, 1):
                    lines.append(f"{i}. {pt}")
                lines.append("")
            if plain.get("detail"):
                lines.append(str(plain["detail"]).strip())
                lines.append("")
        elif isinstance(plain, str) and plain.strip():
            lines.append(plain.strip())
        return "\n".join(lines).strip()

    @staticmethod
    def render_page_html(page: Dict[str, Any], lang: str = "zh") -> str:
        """页面展示用：视觉分段卡片，避免挤成一团。"""
        pro_title = "专业解读" if lang == "zh" else "Professional"
        plain_title = "白话说明" if lang == "zh" else "In plain words"
        summary_l = "一句话" if lang == "zh" else "In one line"
        how_l = "怎么做" if lang == "zh" else "What to do"

        pro_blocks = []
        for p in page.get("professional") or []:
            p = str(p).strip()
            if not p:
                continue
            pro_blocks.append(
                f"<p style='margin:0 0 14px 0;line-height:1.85;color:#333;font-size:0.98rem;'>{p}</p>"
            )
        if not pro_blocks and page.get("content"):
            # 旧数据回退
            return (
                f"<div style='line-height:1.85;white-space:pre-wrap;'>"
                f"{ReportGenerator._escape(str(page.get('content')))}</div>"
            )

        plain = page.get("plain") or {}
        if not isinstance(plain, dict):
            plain = {"summary": str(plain), "points": [], "detail": ""}

        points_html = ""
        pts = plain.get("points") or []
        if pts:
            lis = "".join(
                f"<li style='margin:0 0 10px 0;line-height:1.7;'>{ReportGenerator._escape(str(pt))}</li>"
                for pt in pts
            )
            points_html = (
                f"<div style='font-weight:700;margin:12px 0 6px 0;'>{how_l}</div>"
                f"<ol style='margin:0;padding-left:1.3rem;'>{lis}</ol>"
            )

        summary_html = ""
        if plain.get("summary"):
            summary_html = (
                f"<div style='font-size:1.05rem;font-weight:700;margin-bottom:10px;line-height:1.6;'>"
                f"{summary_l}：{ReportGenerator._escape(str(plain['summary']))}</div>"
            )
        detail_html = ""
        if plain.get("detail"):
            detail_html = (
                f"<p style='margin:12px 0 0 0;line-height:1.85;color:#333;'>"
                f"{ReportGenerator._escape(str(plain['detail']))}</p>"
            )

        return f"""
<div style="display:flex;flex-direction:column;gap:18px;">
  <div style="padding:14px 16px;border:1px solid #e0e0e0;border-radius:10px;background:#fafafa;">
    <div style="font-weight:800;font-size:1.05rem;margin-bottom:12px;color:#424242;">{pro_title}</div>
    {''.join(pro_blocks)}
  </div>
  <div style="padding:16px 18px;border:1px solid #c8e6c9;border-radius:10px;background:#f1f8f4;">
    <div style="font-weight:800;font-size:1.1rem;margin-bottom:12px;color:#2e7d32;">{plain_title}</div>
    {summary_html}
    {points_html}
    {detail_html}
  </div>
</div>
""".strip()

    @staticmethod
    def _escape(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

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
                    "content": (
                        "你是命理顾问。必须输出结构化 JSON："
                        "professional 为段落数组，plain 含 summary/points/detail。"
                        "禁止把整页挤进一个长字符串。不要代码块标记。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.55,
            "max_tokens": 4096,
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
