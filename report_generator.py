"""
九页命理报告 + 可选流年篇章。
Part 1 = 局势研判；Part 2 = 方向与化解（须更进一步、可执行）。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

import requests


class ReportGenerator:
    """生成命理报告（按页请求；事业/财运/感情/健康均含 Part1+Part2）"""

    # Part 1：局势（发生什么、风险、关键月）
    # Part 2：方向与化解（往哪走、如何调候/行为化解、可执行策略）
    PART_RULE_ZH = (
        "【Part 分工·强制】"
        "凡标题含 Part 1：只写「局势研判」——运势起伏、可能事件、注意事项、关键月份；少写长期规划。"
        "凡标题含 Part 2：必须写「方向与化解」——具体方向（行业/资产/关系/调养）、化解方法、行动步骤；"
        "要比 Part 1 更进一步，禁止重复 Part 1 的事件罗列。"
    )
    PART_RULE_EN = (
        "PART RULE: Part 1 = situation forecast (events, risks, key months). "
        "Part 2 = direction & remedies (concrete paths, how to resolve/adjust, actionable steps). "
        "Part 2 must go further than Part 1 — do not repeat Part 1 event lists."
    )

    PAGE_SPECS = [
        ("page1", "八字命盘与基本信息", "四柱十神、藏干、纳音空亡、神煞要点、五行旺衰、大运起运与走势、知进退建议；须引用命盘已算神煞做联动说明"),
        ("page2", "事业详批 (Part 1)", "【局势】当年/近阶段事业运势、可能大事、职场风险与注意事项、关键月份"),
        ("page3", "事业详批 (Part 2)", "【方向与化解】适合的行业与岗位方向、五行喜用对应赛道、瓶颈化解、升迁/转职策略与可执行步骤"),
        ("page4", "财运详批 (Part 1)", "【局势】财运趋势、求财时机、投资适否、旺财/破财月份与风险警示"),
        ("page5", "财运详批 (Part 2)", "【方向与化解】资产配置方向、五行财库思路、理财方式、止损与积累策略、化解破财的具体做法"),
        ("page6", "感情详批 (Part 1)", "【局势】感情事件预测、桃花/人际波动、婚恋风险与注意事项、敏感月份"),
        ("page7", "感情详批 (Part 2)", "【方向与化解】关系经营方向、另一半特质与相处法、环境/风水辅助、矛盾化解与推进时机"),
        ("page8", "健康详批 (Part 1)", "【局势】须结合实岁/虚岁与大运；五行脏腑对应；中年后心血管/血压/代谢风险；易病月份与体检警示（参考非诊断）"),
        ("page9", "健康详批 (Part 2)", "【方向与化解】针对 Part1 风险的调养方向、作息/饮食/运动建议、五行补泻思路、就医检查清单与情绪压力化解（参考非诊断）"),
        ("page10", "流年报告", "当年干支总论；当月（流月）事业·财运·感情·健康注意事项；四季走势与每季1～2个关键流月"),
    ]

    PAGE_SPECS_EN = [
        ("page1", "BaZi Chart & Basics", "Pillars, ten gods, nayin/void, key Shen Sha, five elements, decade luck onset and path"),
        ("page2", "Career (Part 1)", "[Situation] Career outlook, key events, workplace risks, important months"),
        ("page3", "Career (Part 2)", "[Direction & remedy] Industry/role direction, element-aligned paths, bottleneck remedies, promotion/switch steps"),
        ("page4", "Wealth (Part 1)", "[Situation] Wealth trend, timing, investing fit, strong/weak months and risks"),
        ("page5", "Wealth (Part 2)", "[Direction & remedy] Asset allocation direction, money habits, stop-loss/savings strategy, remedies for loss risk"),
        ("page6", "Relationship (Part 1)", "[Situation] Relationship events, romance swings, cautions, sensitive months"),
        ("page7", "Relationship (Part 2)", "[Direction & remedy] How to nurture the bond, partner traits & approach, environment tips, conflict remedies and timing"),
        ("page8", "Health (Part 1)", "[Situation] Age + decade stage; organ map; midlife cardio/BP/metabolic risks; sensitive months; screening alerts (not diagnosis)"),
        ("page9", "Health (Part 2)", "[Direction & remedy] Care direction for Part1 risks; lifestyle/diet/exercise; element-balancing tips; checkup list & stress remedies (not diagnosis)"),
        ("page10", "Annual Luck Report", "Year overview; current month cautions for career/wealth/relationship/health; four seasons with 1–2 key months each"),
    ]

    CORE_PAGE_COUNT = 9  # page1–page9（含健康 Part2）；page10 为流年
    LIUNIAN_KEY = "page10"

    # 四时与地支（命理惯例：季内三支合局气）
    SEASON_SPECS = [
        ("春", "寅卯辰", "约公历2–4月", "木旺 · 生发"),
        ("夏", "巳午未", "约公历5–7月", "火旺 · 发扬"),
        ("秋", "申酉戌", "约公历8–10月", "金旺 · 收敛"),
        ("冬", "亥子丑", "约公历11–次年1月", "水旺 · 蓄养"),
    ]

    SEASON_SPECS_EN = [
        ("Spring", "Yin Mao Chen", "approx. Feb–Apr", "Wood · growth"),
        ("Summer", "Si Wu Wei", "approx. May–Jul", "Fire · expansion"),
        ("Autumn", "Shen You Xu", "approx. Aug–Oct", "Metal · harvest"),
        ("Winter", "Hai Zi Chou", "approx. Nov–Jan", "Water · storage"),
    ]

    FORBIDDEN_PLAIN = (
        "十神、正官、七杀、食神、伤官、正印、偏印、比肩、劫财、正财、偏财、"
        "刑冲合害、干支、天干、地支、藏干、大运、流年、流月、神煞、旺衰、通根、调候、格局、用神、忌神"
    )

    def __init__(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.lang = "zh"

    def _page_specs(self):
        return self.PAGE_SPECS_EN if self.lang == "en" else self.PAGE_SPECS

    def _season_specs(self):
        return self.SEASON_SPECS_EN if self.lang == "en" else self.SEASON_SPECS

    def _lang_rule(self) -> str:
        if self.lang == "en":
            return (
                "LANGUAGE: Write EVERYTHING in English only. "
                "Do not use Chinese characters anywhere in titles or body text."
            )
        if self.lang == "zh_hant":
            return "語言：全篇必須使用繁體中文，禁止簡體字。"
        return "语言：全篇必须使用简体中文。"

    def generate(
        self,
        bazi_data,
        birth_info,
        payment_tier="silver",
        lang: str = "zh",
        progress_callback=None,
    ):
        self.lang = lang if lang in ("zh", "zh_hant", "en") else "zh"
        # 生成时用简体再统一转繁，减少模型不稳定；展示层已有繁体转换
        gen_lang = "zh" if self.lang == "zh_hant" else self.lang
        orig_lang = self.lang
        self.lang = gen_lang

        include_liunian = payment_tier in ("gold", "diamond")
        all_specs = self._page_specs()
        pages = all_specs if include_liunian else all_specs[: self.CORE_PAGE_COUNT]
        context = self._bazi_context(bazi_data, birth_info)

        report: Dict = {}
        total = len(pages)
        for idx, spec in enumerate(pages, 1):
            if callable(progress_callback):
                try:
                    progress_callback(idx - 1, total, spec[1])
                except Exception:
                    pass
            if spec[0] == self.LIUNIAN_KEY:
                chunk = self._generate_liunian_chapter(context, spec)
            else:
                chunk = self._generate_batch(context, [spec])
            report.update(chunk)
            if callable(progress_callback):
                try:
                    progress_callback(idx, total, spec[1])
                except Exception:
                    pass

        self.lang = orig_lang
        fail_pro = (
            "(This page did not generate fully — please regenerate.)"
            if self.lang == "en"
            else ("（本頁生成不完整，請重試）" if self.lang == "zh_hant" else "（本页生成不完整，请重试生成报告）")
        )
        fail_sum = (
            "Generation failed. Please regenerate the report."
            if self.lang == "en"
            else ("本頁生成失敗，請重新生成報告。" if self.lang == "zh_hant" else "本页生成失败，请重新生成报告。")
        )
        for key, title, _ in pages:
            if key not in report or not self._page_has_text(report[key]):
                report[key] = {
                    "title": title,
                    "professional": [f"{fail_pro}"],
                    "plain": {"summary": fail_sum, "points": [], "detail": ""},
                    "content": fail_pro,
                }
            else:
                report[key] = self.sanitize_page_for_display(report[key], title)
                if self.lang == "zh_hant":
                    report[key] = self._to_traditional_page(report[key])
        return report

    @staticmethod
    def resolve_liunian_key(report: Optional[dict]) -> Optional[str]:
        """新版 page10；旧报告若 page9 带四季且非健康标题则为流年。"""
        if not isinstance(report, dict):
            return None
        if "page10" in report:
            return "page10"
        p9 = report.get("page9")
        if isinstance(p9, dict) and p9.get("quarters"):
            title = str(p9.get("title") or "")
            if "健康" in title or "Health" in title:
                return None
            return "page9"
        return None

    @staticmethod
    def is_legacy_liunian_page9(report: Optional[dict]) -> bool:
        """page9 仍是旧版流年（无健康 Part2）时，主报告勿当健康页展示。"""
        return ReportGenerator.resolve_liunian_key(report) == "page9"

    @staticmethod
    def health_part2_missing(report: Optional[dict]) -> bool:
        """主报告缺健康 Part2（需重新生成）。"""
        if not isinstance(report, dict):
            return True
        if ReportGenerator.is_legacy_liunian_page9(report):
            return True
        p9 = report.get("page9")
        if not isinstance(p9, dict):
            return True
        if p9.get("quarters") and ("健康" not in str(p9.get("title") or "") and "Health" not in str(p9.get("title") or "")):
            return True
        return not ReportGenerator._page_has_text(p9)

    @staticmethod
    def _to_traditional_page(page: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from zh_convert import to_traditional
        except Exception:
            return page

        def conv(x: Any) -> Any:
            if isinstance(x, str):
                return to_traditional(x)
            if isinstance(x, list):
                return [conv(i) for i in x]
            if isinstance(x, dict):
                return {k: conv(v) for k, v in x.items()}
            return x

        return conv(page) if isinstance(page, dict) else page

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

    def _age_profile(self, birth_info: dict, bazi_data: dict) -> Dict[str, Any]:
        """实岁/虚岁与年龄段（供健康页与现代体检建议挂钩）。"""
        from datetime import date, datetime

        birth_s = str((birth_info or {}).get("birth_date") or "")
        today = date.today()
        birth = None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                birth = datetime.strptime(birth_s[:10], fmt).date()
                break
            except Exception:
                continue
        if not birth:
            return {"age": None, "age_nominal": None, "band": "", "notes": []}
        age = today.year - birth.year - (
            (today.month, today.day) < (birth.month, birth.day)
        )
        age_nominal = today.year - birth.year + 1
        if age < 18:
            band = "少年"
        elif age < 35:
            band = "青年"
        elif age < 50:
            band = "中年前期"
        elif age < 65:
            band = "中年后期"
        else:
            band = "老年"
        notes = []
        if age >= 45:
            notes.append("现代医学：45岁后心血管、血压、血脂、血糖筛查优先级上升")
        if age >= 50:
            notes.append("现代医学：50岁后更需关注血压、心脏负荷、颈动脉与代谢综合征")
        if age >= 55:
            notes.append("现代医学：55–65岁为高血压、冠心病、心律失常高发段，宜规律体检")
        cur = next((d for d in (bazi_data.get("da_yun") or []) if d.get("is_current")), None)
        if cur:
            notes.append(
                f"当前大运：{cur.get('age_label', '')} {cur.get('gan', '')}{cur.get('zhi', '')}"
            )
        return {
            "age": age,
            "age_nominal": age_nominal,
            "band": band,
            "notes": notes,
            "birth": birth.isoformat(),
        }

    def _health_theory_lines(self, bazi_data: dict, age_profile: dict) -> str:
        """
        命理五脏 + 现代体检角度：火→心/血脉，水→肾/循环，金→肺，木→肝，土→脾胃。
        水火失衡、火克金、官杀攻身等与中年后心血管风险交叉提示（非诊断）。
        """
        wx = bazi_data.get("wuxing_stats") or {}
        # wuxing_stats may be {木: n, ...} or nested
        counts = {}
        if isinstance(wx, dict):
            for k, v in wx.items():
                if isinstance(v, (int, float)):
                    counts[k] = float(v)
                elif isinstance(v, dict) and "count" in v:
                    counts[k] = float(v.get("count") or 0)
        total = sum(counts.values()) or 1.0
        avg = total / 5.0
        lines = []
        organ = {
            "木": "肝胆/筋目/情绪压力",
            "火": "心/小肠/血脉循环/血压心率",
            "土": "脾胃/消化/代谢体重",
            "金": "肺大肠/呼吸/皮肤",
            "水": "肾膀胱/骨骼/泌尿与体液",
        }
        for el, tip in organ.items():
            c = counts.get(el, 0)
            if c <= 0:
                lines.append(f"五行缺{el} → 留意{tip}（偏弱需养）")
            elif c >= avg * 1.6:
                lines.append(f"五行{el}偏旺 → 留意{tip}（过旺宜疏）")
        fire, water, metal = counts.get("火", 0), counts.get("水", 0), counts.get("金", 0)
        if fire >= avg * 1.4 and water < avg:
            lines.append("水火失衡（火偏旺水偏弱）：经典命理提示心火易亢，对应现代需防血压偏高、心悸、失眠")
        if water >= avg * 1.4 and fire < avg:
            lines.append("水多火弱：命理提示心阳不足，对应现代需防循环乏力、畏寒、心脏供血相关不适")
        if metal >= avg and fire >= avg * 1.3:
            lines.append("火金交战倾向：金主肺、火主心，中年后宜同时关注心肺负荷与血压")
        age = age_profile.get("age")
        if age and age >= 50:
            lines.append(
                f"年龄{age}岁（{age_profile.get('band')}）：即使命局平稳，亦应按现代指南定期测血压、血脂、心电图；"
                "若命局再见火旺/水火冲或官杀攻身，须在专业段点名心血管与高血压预防"
            )
        dm = bazi_data.get("day_master") or ""
        if dm in ("庚", "辛") and age and age >= 50:
            lines.append(
                "日主金：金受火克为官杀压力；中年后火运/流年火旺时，命理与现代交叉点常在心肺、血压与情绪性心动过速"
            )
        for n in age_profile.get("notes") or []:
            lines.append(n)
        return "\n".join(f"- {x}" for x in lines) if lines else "- 按五行平衡做常规保养即可"

    def _pillar_detail_lines(self, bazi_data: dict) -> str:
        """把命盘已算字段写入上下文，供报告联动解释（神煞/纳音/空亡等）。"""
        pillars = bazi_data.get("pillars") or {}
        meta = bazi_data.get("meta") or {}
        lines = []
        for name in ("年柱", "月柱", "日柱", "时柱"):
            p = pillars.get(name) or {}
            gan, zhi = p.get("gan", ""), p.get("zhi", "")
            if not gan and name in (bazi_data.get("bazi") or {}):
                gan, zhi = bazi_data["bazi"][name]
            gods = p.get("gan_god") or ""
            nayin = p.get("nayin") or ""
            ss = p.get("shensha") or []
            kong = "空亡" if p.get("is_kong") else ""
            cs = p.get("chang_sheng") or ""
            if self.lang == "en":
                lines.append(
                    f"{name}: {gan}{zhi} god={gods}; nayin={nayin}; "
                    f"stages={cs}; void={bool(p.get('is_kong'))}; "
                    f"ShenSha={','.join(ss) if ss else '-'}"
                )
            else:
                lines.append(
                    f"{name}：{gan}{zhi}（{gods}）；纳音{nayin or '—'}；"
                    f"长生{cs or '—'}；{kong or '非空'}；"
                    f"神煞：{'、'.join(ss) if ss else '无'}"
                )
        kw = meta.get("kongwang_text") or "".join(meta.get("kongwang") or [])
        cg = meta.get("cheng_gu") or {}
        qy = bazi_data.get("qi_yun") or {}
        if self.lang == "en":
            if kw:
                lines.append(f"Day void branches: {kw}")
            if cg.get("total_text"):
                lines.append(f"Bone-weight: {cg.get('total_text')}")
            if qy:
                lines.append(
                    f"Qi Yun: {qy.get('age_label', '')} "
                    f"({'forward' if qy.get('forward') else 'reverse'})"
                )
        else:
            if kw:
                lines.append(f"日空亡：{kw}")
            if cg.get("total_text"):
                lines.append(f"称骨：{cg.get('total_text')}")
            if qy:
                direction = "顺行" if qy.get("forward") else "逆行"
                lines.append(f"起运：{qy.get('age_label', '')}（{direction}）")
        # 大运摘要（前几步 + 当前）
        da_yun = bazi_data.get("da_yun") or []
        brief = []
        for d in da_yun[:6]:
            mark = "*" if d.get("is_current") else ""
            brief.append(
                f"{d.get('age_label', '')}{d.get('gan', '')}{d.get('zhi', '')}{mark}"
            )
        if brief:
            lines.append(("Da Yun: " if self.lang == "en" else "大运：") + " / ".join(brief))
        return "\n".join(lines)

    def _bazi_context(self, bazi_data, birth_info) -> str:
        bazi = bazi_data["bazi"]
        da_yun = bazi_data.get("da_yun") or []
        liu_nian = bazi_data.get("liu_nian") or []
        current_da_yun = next((d for d in da_yun if d.get("is_current")), da_yun[0] if da_yun else None)
        current_liu_nian = next(
            (n for n in liu_nian if n.get("is_current")),
            liu_nian[-1] if liu_nian else None,
        )
        detail = self._pillar_detail_lines(bazi_data)
        age_profile = self._age_profile(birth_info, bazi_data)
        health = self._health_theory_lines(bazi_data, age_profile)
        age_line = ""
        if age_profile.get("age") is not None:
            if self.lang == "en":
                age_line = (
                    f"Age: {age_profile['age']} (nominal {age_profile['age_nominal']}), "
                    f"band: {age_profile['band']}.\n"
                )
            else:
                age_line = (
                    f"当前实岁：{age_profile['age']}岁；虚岁：{age_profile['age_nominal']}岁；"
                    f"年龄段：{age_profile['band']}。\n"
                )
        flow = bazi_data.get("flow") or {}
        def _flow_gz(key: str) -> str:
            item = flow.get(key) or {}
            g, z = item.get("gan") or "", item.get("zhi") or ""
            return f"{g}{z}" if g or z else ""
        flow_line = ""
        if flow:
            if self.lang == "en":
                flow_line = (
                    f"Current pillars — Da Yun: {_flow_gz('da_yun')}; "
                    f"Year: {_flow_gz('liu_nian')}; Month: {_flow_gz('liu_yue')}; "
                    f"Day: {_flow_gz('liu_ri')}. "
                    f"Calendar hint: year={(flow.get('liu_nian') or {}).get('year', '')}, "
                    f"month={(flow.get('liu_yue') or {}).get('month', '')}.\n"
                )
            else:
                flow_line = (
                    f"【当前运势柱】大运{_flow_gz('da_yun')}；"
                    f"流年{_flow_gz('liu_nian')}（{(flow.get('liu_nian') or {}).get('year', '')}年）；"
                    f"流月{_flow_gz('liu_yue')}（{(flow.get('liu_yue') or {}).get('month', '')}月）；"
                    f"流日{_flow_gz('liu_ri')}。"
                    f"《流年报告》必须重点展开「当年」与「当月」四维：事业·财运·感情·健康。\n"
                )
        if self.lang == "en":
            dy = (
                f"Step {current_da_yun.get('step')} {current_da_yun.get('gan')}{current_da_yun.get('zhi')} "
                f"{current_da_yun.get('years', '')}"
                if current_da_yun
                else "unknown"
            )
            ln = (
                f"{current_liu_nian['year']} {current_liu_nian['gan']}{current_liu_nian['zhi']}"
                if current_liu_nian
                else "unknown"
            )
            return (
                f"Name: {birth_info.get('name', 'User')}; Gender: {bazi_data.get('gender')}; "
                f"Birth: {birth_info.get('birth_date', '')}; {age_line}{flow_line}"
                f"BaZi: Year {bazi['年柱'][0]}{bazi['年柱'][1]} "
                f"Month {bazi['月柱'][0]}{bazi['月柱'][1]} "
                f"Day {bazi['日柱'][0]}{bazi['日柱'][1]} "
                f"Hour {bazi['时柱'][0]}{bazi['时柱'][1]}; "
                f"Day Master: {bazi_data.get('day_master')}; "
                f"Five elements: {json.dumps(bazi_data.get('wuxing_stats', {}), ensure_ascii=False)}; "
                f"Current decade luck: {dy}; Current year luck: {ln}.\n"
                f"Chart details (must use in analysis, especially page1):\n{detail}\n"
                f"Health bridge (BaZi organs × modern screening; health Part1+Part2 must use age):\n{health}\n"
                "Tie Shen Sha / nayin / void / decade luck to the narrative — do not invent stars not listed. "
                "Health Part1 = risks/situation; Health Part2 = remedies and checkup direction. "
                "Page8/9 must name age-appropriate risks (e.g. 55+ cardio/BP) when chart supports it. "
                "For Annual Luck Report use four seasons "
                "(Spring Yin-Mao-Chen, Summer Si-Wu-Wei, Autumn Shen-You-Xu, Winter Hai-Zi-Chou); "
                "name 1–2 key months per season, not a 12-month laundry list."
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
            f"出生：{birth_info.get('birth_date', '')}；{age_line}{flow_line}"
            f"八字：年{bazi['年柱'][0]}{bazi['年柱'][1]} "
            f"月{bazi['月柱'][0]}{bazi['月柱'][1]} "
            f"日{bazi['日柱'][0]}{bazi['日柱'][1]} "
            f"时{bazi['时柱'][0]}{bazi['时柱'][1]}；"
            f"日主：{bazi_data.get('day_master')}；"
            f"五行：{json.dumps(bazi_data.get('wuxing_stats', {}), ensure_ascii=False)}；"
            f"当前大运：{dy}；当前流年：{ln}。\n"
            f"【命盘明细·报告须联动引用，尤其第1页；勿编造未列出的神煞】\n{detail}\n"
            f"【健康交叉提示·健康 Part1/Part2 必须结合年龄】\n{health}\n"
            "说明：八字脏腑对应仅作体质倾向，须结合年龄与现代体检建议书写；禁止恐吓，强调「参考+就医」。"
            "健康 Part1 写局势与风险；健康 Part2 写调养方向与化解，勿重复 Part1。"
            "分析结合流年与命局；《流年报告》按四时分述（春寅卯辰、夏巳午未、秋申酉戌、冬亥子丑），"
            "每季点出一至两个关键流月，勿写成十二个月流水账。"
        )

    def _generate_liunian_chapter(self, context: str, spec: tuple) -> Dict:
        """独立篇章《流年报告》：当年总论 + 当月四维 + 四季。"""
        key, title, focus = spec
        seasons = self._season_specs()
        seasons_hint = "\n".join(
            f"- {name}（{zhi}，{cal}，{wx}）" for name, zhi, cal, wx in seasons
        )
        lang_rule = self._lang_rule()
        if self.lang == "en":
            prompt = f"""Write the independent chapter 《{title}》. Valid JSON only, no markdown fences.

{lang_rule}

Chart: {context}
Focus: {focus}

Seasons:
{seasons_hint}

Output:
"{key}": {{
  "title": "{title}",
  "professional": [
    "This year's stem-branch vs natal chart — overall climate (70-100 words)",
    "Career & wealth rhythm for the YEAR (70-100 words)",
    "Relationship & health for the YEAR (70-100 words)",
    "Strongest vs caution periods this year (70-100 words)"
  ],
  "current_month": {{
    "label": "current month pillar from context (e.g. 2026 Jul · Yi Wei)",
    "overview": "why this month matters vs year luck (50-80 words)",
    "career": "career cautions/opportunities this month (40-70 words)",
    "wealth": "money/investing cautions this month (40-70 words)",
    "relationship": "relationship/people cautions this month (40-70 words)",
    "health": "health cautions this month, age-aware (40-70 words)",
    "action": "3 concrete do / don't for this month (40-60 words)"
  }},
  "quarters": [
    {{"name":"Spring","branch":"Yin Mao Chen","months":"approx. Feb–Apr","outlook":"60-90 words","focus_months":"1–2 key months","advice":"40-60 words"}},
    {{"name":"Summer","branch":"Si Wu Wei","months":"approx. May–Jul","outlook":"...","focus_months":"...","advice":"..."}},
    {{"name":"Autumn","branch":"Shen You Xu","months":"approx. Aug–Oct","outlook":"...","focus_months":"...","advice":"..."}},
    {{"name":"Winter","branch":"Hai Zi Chou","months":"approx. Nov–Jan","outlook":"...","focus_months":"...","advice":"..."}}
  ],
  "plain": {{
    "summary":"one plain line on this year + this month (≤40 words, zero jargon)",
    "points":["tip1","tip2","tip3"],
    "detail":"90-130 words plain English covering year then this month",
    "quarters_plain":[
      {{"name":"Spring","summary":"≤30 words","tips":["A","B"]}},
      {{"name":"Summer","summary":"...","tips":["...","..."]}},
      {{"name":"Autumn","summary":"...","tips":["...","..."]}},
      {{"name":"Winter","summary":"...","tips":["...","..."]}}
    ]
  }}
}}

Hard rules: current_month REQUIRED with all four domains; exactly 4 seasons; plain forbids jargon ({self.FORBIDDEN_PLAIN}).
"""
        else:
            prompt = f"""根据命盘写独立篇章《{title}》。只输出合法 JSON，不要 markdown 代码块。

{lang_rule}

命盘：{context}
主题：{focus}

【专业写法·强制】
1) 先写「当年」流年干支相对命局的总气候，再分事业·财运·感情·健康四维。
2) 必须单列「当月」：用上下文中的流月干支与公历月份，写清本月注意事项；
   当月同样覆盖事业·财运·感情·健康，并给出可执行的做/不做。
3) 四季：春寅卯辰、夏巳午未、秋申酉戌、冬亥子丑；每季只点 1～2 个关键流月，勿十二个月流水账。
4) 语气专业、具体，避免空话；健康结合年龄，强调参考非诊断。

四季对照：
{seasons_hint}

【输出】
"{key}": {{
  "title": "{title}",
  "professional": [
    "流年总论：今年干支与命局大势（70-100字）",
    "当年事业与财运节奏（70-100字）",
    "当年感情/人际与健康提要（70-100字）",
    "全年最旺与需防时段（70-100字）"
  ],
  "current_month": {{
    "label": "当月标签，如：2026年7月 · 乙未月",
    "overview": "当月相对流年的气机要点（50-80字）",
    "career": "本月事业注意/机遇（40-70字）",
    "wealth": "本月财运注意/机遇（40-70字）",
    "relationship": "本月感情与人际注意（40-70字）",
    "health": "本月健康注意（结合年龄，40-70字）",
    "action": "本月三条做与不做（40-60字）"
  }},
  "quarters": [
    {{"name":"春季","branch":"寅卯辰","months":"约2–4月","outlook":"本季专业判断60-90字","focus_months":"点出1～2个关键流月或节气","advice":"本季行动建议40-60字"}},
    {{"name":"夏季","branch":"巳午未","months":"约5–7月","outlook":"...","focus_months":"...","advice":"..."}},
    {{"name":"秋季","branch":"申酉戌","months":"约8–10月","outlook":"...","focus_months":"...","advice":"..."}},
    {{"name":"冬季","branch":"亥子丑","months":"约11–次年1月","outlook":"...","focus_months":"...","advice":"..."}}
  ],
  "plain": {{
    "summary":"一句人话：今年基调 + 本月最该注意什么（≤40字，零术语）",
    "points":["全年建议1","本月建议2","本月建议3"],
    "detail":"90-130字白话：先说全年，再说本月四维怎么做",
    "quarters_plain":[
      {{"name":"春季","summary":"本季人话≤30字","tips":["建议A","建议B"]}},
      {{"name":"夏季","summary":"...","tips":["...","..."]}},
      {{"name":"秋季","summary":"...","tips":["...","..."]}},
      {{"name":"冬季","summary":"...","tips":["...","..."]}}
    ]
  }}
}}

硬性要求：必须含 current_month 且四维齐全；quarters 恰好四季；plain 严禁 {self.FORBIDDEN_PLAIN}
"""
        raw = self._call_deepseek(prompt)
        parsed = self._parse_json_loose(raw)
        if isinstance(parsed, dict) and key not in parsed:
            if "quarters" in parsed or "professional" in parsed or "current_month" in parsed:
                parsed = {key: parsed}
        item = parsed.get(key) if isinstance(parsed, dict) else None
        page = self._coerce_page(item, title, raw)
        if isinstance(item, dict) and isinstance(item.get("current_month"), dict):
            page["current_month"] = item["current_month"]
        page = self._normalize_current_month(page, context)
        page = self._normalize_quarters(page)
        page = self._ensure_plain_section(page, title)
        page = self._ensure_quarters_plain(page)
        page["content"] = ReportGenerator.build_content_markdown(page)
        return {key: page}

    def _normalize_current_month(self, page: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        cm = page.get("current_month") if isinstance(page.get("current_month"), dict) else {}
        fields = ("label", "overview", "career", "wealth", "relationship", "health", "action")
        filled = {k: str(cm.get(k) or "").strip() for k in fields}
        if sum(1 for k in ("career", "wealth", "relationship", "health") if filled[k]) >= 3:
            page["current_month"] = filled
            return page
        # 弱结果：用上下文补一层专业壳，避免当月空白
        if self.lang == "en":
            page["current_month"] = {
                "label": filled["label"] or "Current month",
                "overview": filled["overview"] or "Read this month against the year pillar; pace decisions.",
                "career": filled["career"] or "Keep delivery steady; avoid abrupt role gambles mid-month.",
                "wealth": filled["wealth"] or "Prefer cash-flow clarity; delay large speculative bets.",
                "relationship": filled["relationship"] or "Clarify expectations; don't escalate minor friction.",
                "health": filled["health"] or "Sleep, blood pressure, and recovery matter more than intensity.",
                "action": filled["action"] or "Do: one priority weekly review. Don't: stack three big decisions in one week.",
            }
        else:
            page["current_month"] = {
                "label": filled["label"] or "当月（见流月）",
                "overview": filled["overview"] or "本月气机宜对照流年总势看：宜稳中有序，忌冲动拍板。",
                "career": filled["career"] or "事业：先收口在办事项，重大跳槽/签约尽量避开月中冲动窗口。",
                "wealth": filled["wealth"] or "财运：以现金流与账目清晰为先，大额投机与盲目加杠杆宜缓。",
                "relationship": filled["relationship"] or "感情人际：把话说清边界，小摩擦勿升级成立场战。",
                "health": filled["health"] or "健康：作息与血压/心肺负荷优先，强度训练量力，不适即停并体检。",
                "action": filled["action"] or "做：每周一次重点复盘。不做：一周内连开三件大事。",
            }
        return page

    def _normalize_quarters(self, page: Dict[str, Any]) -> Dict[str, Any]:
        raw = page.get("quarters")
        seasons = self._season_specs()
        if not isinstance(raw, list) or not raw:
            if self.lang == "en":
                page["quarters"] = [
                    {
                        "name": name,
                        "branch": zhi,
                        "months": cal,
                        "outlook": f"{name} outlook needs regeneration to complete.",
                        "focus_months": "Watch mid-season solar terms",
                        "advice": "Move steadily; leave room for important decisions.",
                    }
                    for name, zhi, cal, _wx in seasons
                ]
            else:
                page["quarters"] = [
                    {
                        "name": f"{name}季",
                        "branch": zhi,
                        "months": cal,
                        "outlook": f"{name}季运势需结合流年再看（可重试生成以补全）。",
                        "focus_months": "关注季中节气前后",
                        "advice": "稳妥行事，重大决定留有余地。",
                    }
                    for name, zhi, cal, _wx in seasons
                ]
            return page
        fixed = []
        for i, (name, zhi, cal, _wx) in enumerate(seasons):
            src = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
            default_name = name if self.lang == "en" else f"{name}季"
            fixed.append(
                {
                    "name": str(src.get("name") or default_name),
                    "branch": str(src.get("branch") or zhi),
                    "months": str(src.get("months") or cal),
                    "outlook": str(src.get("outlook") or "").strip(),
                    "focus_months": str(src.get("focus_months") or src.get("关键月") or "").strip(),
                    "advice": str(src.get("advice") or src.get("建议") or "").strip(),
                }
            )
        page["quarters"] = fixed
        return page

    def _ensure_quarters_plain(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """四季白话本地推导，不再二次调用 API。"""
        plain = page.get("plain") if isinstance(page.get("plain"), dict) else {}
        qp = plain.get("quarters_plain")
        if isinstance(qp, list) and len(qp) >= 4 and all(
            isinstance(x, dict) and str(x.get("summary") or "").strip() for x in qp[:4]
        ):
            page["plain"] = plain
            return page

        quarters = page.get("quarters") or []
        plain["quarters_plain"] = []
        seasons = self.SEASON_SPECS_EN if self.lang == "en" else self.SEASON_SPECS
        for i, (name, *_rest) in enumerate(seasons):
            src = quarters[i] if i < len(quarters) and isinstance(quarters[i], dict) else {}
            outlook = str(src.get("outlook") or "").strip()
            advice = str(src.get("advice") or "").strip()
            focus = str(src.get("focus_months") or "").strip()
            default_name = name if self.lang == "en" else f"{name}季"
            if self.lang == "en":
                summary = outlook[:80] if outlook else f"Adjust pacing through {name.lower()}."
                tips = [t for t in (advice, focus) if t][:2] or [
                    "Don't rush big moves early in the season",
                    "Review mid-season, decide at the end",
                ]
            else:
                summary = (outlook[:40] if outlook else f"{name}季宜顺势调整节奏。")
                tips = [t for t in (advice, focus) if t][:2] or [
                    "大事不赶在季初硬推",
                    "季中做检视，季末再定下一步",
                ]
            plain["quarters_plain"].append(
                {
                    "name": str(src.get("name") or default_name),
                    "summary": summary,
                    "tips": [str(t).strip() for t in tips if str(t).strip()][:3],
                }
            )
        page["plain"] = plain
        return page

    def _generate_batch(self, context: str, batch: List) -> Dict:
        keys = [b[0] for b in batch]
        specs = "\n".join(f"- {k}: 《{title}》主题：{focus}" for k, title, focus in batch)
        key0 = keys[0]
        lang_rule = self._lang_rule()
        if self.lang == "en":
            prompt = f"""Write a BaZi report page from the chart. Output valid JSON only, no markdown fences.

{lang_rule}
{self.PART_RULE_EN}

Chart: {context}

Pages to generate:
{specs}

Structure for each page:
"{key0}": {{
  "title": "page title in English",
  "professional": [
    "paragraph 1 (60-90 words)",
    "paragraph 2 (60-90 words)",
    "paragraph 3 (60-90 words)",
    "paragraph 4 (60-90 words)"
  ],
  "plain": {{
    "summary": "one plain line (≤40 words, zero jargon)",
    "points": ["tip1", "tip2", "tip3"],
    "detail": "80-120 words like talking to a friend, zero jargon"
  }}
}}

Hard rules:
1) professional must be an array of exactly 4 strings.
2) plain.points must be 3 short tips.
3) plain must never use: {self.FORBIDDEN_PLAIN}
4) Professional may use BaZi terms; plain must not.
5) Entire output in English.
6) Obey PART RULE strictly for Part 1 vs Part 2 pages.
"""
        else:
            prompt = f"""根据命盘写命理报告。只输出合法 JSON，不要 markdown 代码块。

{lang_rule}
{self.PART_RULE_ZH}

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
    "第四段：风险与应对 / 或化解步骤（约60-90字）"
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
6) title 只能是纯中文/英文标题字符串，禁止出现 {{、}}、"page1"、JSON 片段。
7) 第1页须引用上下文中的神煞/纳音/空亡/大运，勿编造未列出的神煞。
8) 严格遵守 Part 1=局势、Part 2=方向与化解；Part 2 禁止复述 Part 1 事件清单。
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
            # 解析失败时尝试从原文抽 professional 数组
            if not isinstance(item, dict) or not item.get("professional"):
                recovered = self._recover_page_from_raw(raw, key, title)
                if recovered:
                    item = recovered
            page = self._coerce_page(item, title, raw if key == keys[0] else "")
            page = self._ensure_professional_section(page, title, context)
            page = self._ensure_plain_section(page, title)
            out[key] = page
        return out

    def _professional_weak(self, page: Dict[str, Any], title: str) -> bool:
        pro = page.get("professional") or []
        if not isinstance(pro, list):
            return True
        paras = [str(p).strip() for p in pro if str(p).strip()]
        if len(paras) < 2:
            return True
        # 误把标题当成唯一正文
        if len(paras) == 1 and paras[0].replace(" ", "") in {
            title.replace(" ", ""),
            title.replace(" ", "") + "。",
        }:
            return True
        if all(len(p) < 25 for p in paras):
            return True
        if all(
            ("生成不完整" in p) or ("专业解读缺失" in p) or ("需重新生成" in p) or ("did not generate" in p.lower())
            for p in paras
        ):
            return True
        return False

    def _ensure_professional_section(
        self, page: Dict[str, Any], title: str, context: str
    ) -> Dict[str, Any]:
        """专业段缺失时用本地兜底，不再二次调用 API（避免重新生成卡住）。"""
        if not self._professional_weak(page, title):
            return page
        _ = context  # 保留签名兼容；兜底不依赖二次请求
        if self.lang == "en":
            page["professional"] = [
                f"{title}: chart structure and day master set the tone for this reading.",
                "Five-element balance and current decade luck show where pressure and support sit.",
                "Key stars and voids on the pillars should be read with the decade timeline, not alone.",
                "Use this page as the map; later pages apply it to career, wealth, relationship, and health.",
            ]
        else:
            page["professional"] = [
                f"就「{title}」而言：先以日主与四柱十神定格局基调，再看月令与地支藏干是否通根得气。",
                "五行旺衰与当前大运、流年形成「体用」关系：旺者宜疏、弱者宜扶，知进退比空谈格局更重要。",
                "命盘已标神煞、纳音与空亡，应与大运时间轴对照阅读，勿脱离岁运单独论吉凶。",
                "本页是总图；事业、财运、感情、健康各页须回扣此处的日主强弱与用忌方向。",
            ]
        page["content"] = ReportGenerator.build_content_markdown(page)
        return page

    @staticmethod
    def _clean_pro_paragraph(text: str) -> str:
        s = ReportGenerator._strip_json_artifacts(str(text or "").strip())
        if ReportGenerator._looks_like_json_blob(s):
            # 尝试从 blob 抽数组元素
            recovered = ReportGenerator._extract_professional_list(s)
            if recovered:
                return recovered[0]
            return ""
        return s

    @staticmethod
    def _extract_professional_list(text: str) -> List[str]:
        if not text:
            return []
        # 直接 JSON
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                pro = obj.get("professional")
                if isinstance(pro, list):
                    return [str(x).strip() for x in pro if str(x).strip()]
                for v in obj.values():
                    if isinstance(v, dict) and isinstance(v.get("professional"), list):
                        return [str(x).strip() for x in v["professional"] if str(x).strip()]
        except Exception:
            pass
        m = re.search(r'"professional"\s*:\s*\[(.*?)\]', text, flags=re.S)
        if not m:
            return []
        body = m.group(1)
        parts = re.findall(r'"((?:\\.|[^"\\])*)"', body)
        out = []
        for p in parts:
            p = p.replace('\\"', '"').replace("\\n", "\n").strip()
            if p and not p.startswith("page") and len(p) >= 8:
                out.append(p)
        return out

    def _recover_page_from_raw(self, raw: str, key: str, title: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        parsed = self._parse_json_loose(raw)
        if isinstance(parsed, dict):
            if key in parsed and isinstance(parsed[key], dict):
                return parsed[key]
            if "professional" in parsed:
                return parsed
        pro = self._extract_professional_list(raw)
        if len(pro) >= 2:
            return {"title": title, "professional": pro, "plain": {}}
        return None

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
        """白话缺失时从专业段本地推导，不再二次调用 API。"""
        plain = page.get("plain") if isinstance(page.get("plain"), dict) else {}
        if not self._plain_missing(plain):
            page["content"] = ReportGenerator.build_content_markdown(page)
            return page

        pro_list = [str(p).strip() for p in (page.get("professional") or []) if str(p).strip()]
        pro_text = "\n".join(pro_list)
        first = re.split(r"[。！？.!?]", pro_text)[0].strip() if pro_text else ""
        if self.lang == "en":
            filled = {
                "summary": (
                    ((first[:70] + "…") if len(first) > 70 else first)
                    if first
                    else f"Key takeaways for {title}."
                ),
                "points": [
                    "Do the one most important task first.",
                    "Don't launch too many new plans at once.",
                    "If unsure, wait a few days before deciding.",
                ],
                "detail": (
                    "Skip the jargon above for now. In plain terms: pace yourself, "
                    "clarify priorities, and leave room to adjust."
                ),
            }
        else:
            filled = {
                "summary": (
                    ((first[:36] + "…") if len(first) > 36 else first)
                    if first
                    else "先看这几条可执行建议"
                ),
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
        if isinstance(plain, dict) and plain.get("quarters_plain"):
            filled["quarters_plain"] = plain["quarters_plain"]
        page["plain"] = filled
        page["content"] = ReportGenerator.build_content_markdown(page)
        return page

    def _coerce_page(self, item: Any, title: str, fallback_raw: str = "") -> Dict[str, Any]:
        if isinstance(item, str) and item.strip():
            cleaned = ReportGenerator._strip_json_artifacts(item.strip())
            if ReportGenerator._looks_like_json_blob(cleaned):
                item = None
            else:
                page = ReportGenerator._split_legacy_content(cleaned, title)
                page["title"] = ReportGenerator.sanitize_title(page.get("title"), title)
                page["professional"] = [
                    ReportGenerator._strip_json_artifacts(p)
                    for p in (page.get("professional") or [])
                    if not ReportGenerator._looks_like_json_blob(p)
                ] or [f"（{title}专业解读缺失）"]
                page["content"] = ReportGenerator.build_content_markdown(page)
                return page
        if not isinstance(item, dict):
            # 禁止把原始 JSON 残片塞进正文
            msg = f"（{title}生成不完整，请重新生成报告）"
            if fallback_raw and not ReportGenerator._looks_like_json_blob(fallback_raw):
                msg = ReportGenerator._strip_json_artifacts(fallback_raw[:500]) or msg
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
            paragraphs = ReportGenerator._split_paragraphs(
                ReportGenerator._strip_json_artifacts(pro)
            )
        elif isinstance(pro, list):
            paragraphs = []
            for x in pro:
                raw = str(x).strip()
                if ReportGenerator._looks_like_json_blob(raw) or '"professional"' in raw:
                    paragraphs.extend(ReportGenerator._extract_professional_list(raw))
                    continue
                s = ReportGenerator._clean_pro_paragraph(raw)
                if s and len(s) >= 8:
                    paragraphs.append(s)
        else:
            paragraphs = []

        # 若 professional 字段缺失但 raw/content 含数组，再抽一次
        if len(paragraphs) < 2 and fallback_raw:
            paragraphs = ReportGenerator._extract_professional_list(fallback_raw) or paragraphs
        if len(paragraphs) < 2 and item.get("content"):
            paragraphs = ReportGenerator._extract_professional_list(str(item.get("content"))) or paragraphs

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
            if plain_raw.get("quarters_plain"):
                plain["quarters_plain"] = plain_raw.get("quarters_plain")
        else:
            plain = {"summary": "", "points": [], "detail": ""}

        # 兼容旧模型只返回 content
        if (not paragraphs or self._plain_missing(plain)) and item.get("content"):
            content_s = ReportGenerator._strip_json_artifacts(str(item.get("content")))
            if not ReportGenerator._looks_like_json_blob(content_s):
                legacy = ReportGenerator._split_legacy_content(content_s, title)
                if not paragraphs:
                    paragraphs = legacy.get("professional") or []
                if self._plain_missing(plain):
                    plain = legacy.get("plain") or plain

        if not paragraphs:
            paragraphs = [f"（{title}专业解读缺失）"]

        page = {
            "title": ReportGenerator.sanitize_title(
                item.get("title") or item.get("标题"), title
            ),
            "professional": paragraphs,
            "plain": plain,
        }
        if item.get("quarters"):
            page["quarters"] = item.get("quarters")
        if isinstance(item.get("current_month"), dict):
            page["current_month"] = item.get("current_month")
        page["content"] = ReportGenerator.build_content_markdown(page)
        return page

    @staticmethod
    def _looks_like_json_blob(text: str) -> bool:
        s = (text or "").strip()
        if not s:
            return False
        if s.startswith("{") or s.startswith("["):
            return True
        if re.search(r'"page\d+"\s*:', s) or re.search(r'\{\s*"page\d+"', s):
            return True
        if '"title"' in s and '"professional"' in s and "{" in s:
            return True
        return False

    @staticmethod
    def _strip_json_artifacts(text: str) -> str:
        """去掉模型泄漏的 JSON 外壳残片。绝不把整页 JSON 收成「仅标题」。"""
        if not text:
            return ""
        s = str(text).strip()
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
        # 整页/含 professional 的 JSON：优先抽出正文数组，禁止退化成 title
        if '"professional"' in s or re.search(r'"page\d+"\s*:', s):
            pro = ReportGenerator._extract_professional_list(s)
            if pro:
                return "\n\n".join(pro)
            # 无法抽出则原样返回，交给 looks_like_json_blob 过滤
            return s
        # 仅标题残片：{ "title": "xxx"
        m2 = re.match(r'^\{\s*"title"\s*:\s*"(.*?)"\s*,?\s*\}?\s*$', s, flags=re.S)
        if m2 and m2.group(1) and len(m2.group(1)) < 80:
            return m2.group(1).strip()
        # 去掉误粘在正文前的短前缀
        s = re.sub(r'^\{\s*"page\d+"\s*:\s*\{\s*', "", s, count=1)
        s = s.strip().strip('{}" \n')
        return s

    @staticmethod
    def sanitize_title(raw: Any, fallback: str) -> str:
        title = str(raw or "").strip()
        if ReportGenerator._looks_like_json_blob(title) or '"page' in title:
            m = re.search(r'"title"\s*:\s*"([^"]{2,60})"', title)
            if m:
                title = m.group(1).strip()
            else:
                return fallback
        title = re.sub(r'^["\{\[\s]+', "", title)
        title = re.sub(r'["\}\]\s]+$', "", title)
        title = title.strip()
        if not title or len(title) > 80:
            return fallback
        if re.search(r"page\d+|professional|plain", title, flags=re.I):
            return fallback
        return title

    @staticmethod
    def sanitize_page_for_display(page: Any, fallback_title: str = "") -> Dict[str, Any]:
        """展示/PDF 前清洗旧报告中的 JSON 残片。"""
        if not isinstance(page, dict):
            return {
                "title": fallback_title or "报告",
                "professional": [str(page)],
                "plain": {"summary": "", "points": [], "detail": ""},
                "content": str(page),
            }
        out = dict(page)
        title = ReportGenerator.sanitize_title(out.get("title"), fallback_title or "报告")
        out["title"] = title
        pro = out.get("professional") or []
        cleaned: List[str] = []
        if isinstance(pro, list):
            for p in pro:
                raw = str(p).strip()
                if ReportGenerator._looks_like_json_blob(raw) or '"professional"' in raw:
                    cleaned.extend(ReportGenerator._extract_professional_list(raw))
                    continue
                s = ReportGenerator._strip_json_artifacts(raw)
                if not s or ReportGenerator._looks_like_json_blob(s):
                    continue
                # 过滤「只有标题」伪正文
                if s.replace(" ", "") in {title.replace(" ", ""), title.replace(" ", "") + "。"}:
                    continue
                cleaned.append(s)
        elif isinstance(pro, str):
            if ReportGenerator._looks_like_json_blob(pro) or '"professional"' in pro:
                cleaned = ReportGenerator._extract_professional_list(pro)
            else:
                s = ReportGenerator._strip_json_artifacts(pro)
                if s and not ReportGenerator._looks_like_json_blob(s):
                    cleaned = [s]
        # 去重保序
        uniq = []
        for x in cleaned:
            if x and x not in uniq:
                uniq.append(x)
        if len(uniq) < 2:
            out["professional"] = [
                f"（{title}专业解读不完整，请重新生成报告以获得完整四段分析。）"
            ]
        else:
            out["professional"] = uniq
        # 保留流年当月块
        if isinstance(page.get("current_month"), dict):
            out["current_month"] = page["current_month"]
        if isinstance(page.get("quarters"), list):
            out["quarters"] = page["quarters"]
        content = out.get("content")
        if content and ReportGenerator._looks_like_json_blob(str(content)):
            out["content"] = ReportGenerator.build_content_markdown(out)
        return out

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
        cm = page.get("current_month") if isinstance(page.get("current_month"), dict) else None
        if cm:
            lines.append("#### 当月注意事项（事业·财运·感情·健康）")
            lines.append("")
            if cm.get("label"):
                lines.append(f"**{cm['label']}**")
                lines.append("")
            for lab, key in (
                ("总览", "overview"),
                ("事业", "career"),
                ("财运", "wealth"),
                ("感情", "relationship"),
                ("健康", "health"),
                ("行动", "action"),
            ):
                if cm.get(key):
                    lines.append(f"**{lab}：** {cm[key]}")
                    lines.append("")
        quarters = page.get("quarters") or []
        if quarters:
            lines.append("#### 四季流年")
            lines.append("")
            for q in quarters:
                if not isinstance(q, dict):
                    continue
                lines.append(
                    f"**{q.get('name', '')}（{q.get('branch', '')} · {q.get('months', '')}）**"
                )
                lines.append("")
                if q.get("outlook"):
                    lines.append(str(q["outlook"]))
                    lines.append("")
                if q.get("focus_months"):
                    lines.append(f"关键月：{q['focus_months']}")
                    lines.append("")
                if q.get("advice"):
                    lines.append(f"建议：{q['advice']}")
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
            qp = plain.get("quarters_plain") or []
            if qp:
                lines.append("**四季白话：**")
                lines.append("")
                for q in qp:
                    if not isinstance(q, dict):
                        continue
                    lines.append(f"- **{q.get('name', '')}**：{q.get('summary', '')}")
                    for tip in q.get("tips") or []:
                        lines.append(f"  - {tip}")
                lines.append("")
        elif isinstance(plain, str) and plain.strip():
            lines.append(plain.strip())
        return "\n".join(lines).strip()

    @staticmethod
    def render_page_html(page: Dict[str, Any], lang: str = "zh") -> str:
        """页面展示用：视觉分段卡片，避免挤成一团。"""
        page = ReportGenerator.sanitize_page_for_display(
            page if isinstance(page, dict) else {},
            str((page or {}).get("title") or "") if isinstance(page, dict) else "",
        )
        if lang == "zh_hant":
            try:
                page = ReportGenerator._to_traditional_page(page) if isinstance(page, dict) else page
            except Exception:
                pass
            pro_title, plain_title = "專業解讀", "白話說明"
            season_title, summary_l = "四季流年預測", "一句話"
            how_l, focus_l, advice_l = "怎麼做", "關鍵月", "建議"
            season_tips = "四季白話"
            month_title = "當月注意（事業 · 財運 · 感情 · 健康）"
            month_labs = {
                "overview": "總覽", "career": "事業", "wealth": "財運",
                "relationship": "感情", "health": "健康", "action": "行動",
            }
        elif lang == "en":
            pro_title, plain_title = "Professional", "In plain words"
            season_title, summary_l = "Seasonal outlook", "In one line"
            how_l, focus_l, advice_l = "What to do", "Key months", "Advice"
            season_tips = "Season tips"
            month_title = "This month (Career · Wealth · Relationship · Health)"
            month_labs = {
                "overview": "Overview", "career": "Career", "wealth": "Wealth",
                "relationship": "Relationship", "health": "Health", "action": "Actions",
            }
        else:
            pro_title, plain_title = "专业解读", "白话说明"
            season_title, summary_l = "四季流年预测", "一句话"
            how_l, focus_l, advice_l = "怎么做", "关键月", "建议"
            season_tips = "四季白话"
            month_title = "当月注意（事业 · 财运 · 感情 · 健康）"
            month_labs = {
                "overview": "总览", "career": "事业", "wealth": "财运",
                "relationship": "感情", "health": "健康", "action": "行动",
            }

        pro_blocks = []
        for p in page.get("professional") or []:
            p = str(p).strip()
            if not p:
                continue
            pro_blocks.append(
                f"<p style='margin:0 0 14px 0;line-height:1.85;color:#333;font-size:0.98rem;'>{p}</p>"
            )
        if not pro_blocks and page.get("content") and not page.get("quarters") and not page.get("current_month"):
            return (
                f"<div style='line-height:1.85;white-space:pre-wrap;'>"
                f"{ReportGenerator._escape(str(page.get('content')))}</div>"
            )

        month_html = ""
        cm = page.get("current_month") if isinstance(page.get("current_month"), dict) else None
        if cm and any(cm.get(k) for k in ("overview", "career", "wealth", "relationship", "health", "action")):
            rows = []
            if cm.get("label"):
                rows.append(
                    f"<div style='font-weight:800;color:#e65100;margin-bottom:8px;'>"
                    f"{ReportGenerator._escape(str(cm['label']))}</div>"
                )
            for key in ("overview", "career", "wealth", "relationship", "health", "action"):
                if not cm.get(key):
                    continue
                rows.append(
                    f"<div style='margin:0 0 10px 0;padding:10px 12px;background:#fff;"
                    f"border-radius:8px;border:1px solid #ffe0b2;'>"
                    f"<div style='font-weight:700;color:#ef6c00;margin-bottom:4px;'>"
                    f"{month_labs.get(key, key)}</div>"
                    f"<div style='line-height:1.75;color:#333;'>"
                    f"{ReportGenerator._escape(str(cm[key]))}</div></div>"
                )
            month_html = (
                f"<div style='padding:14px 16px;border:1px solid #ffcc80;border-radius:10px;"
                f"background:#fff8e1;'>"
                f"<div style='font-weight:800;font-size:1.05rem;margin-bottom:12px;color:#e65100;'>"
                f"{month_title}</div>{''.join(rows)}</div>"
            )

        season_html = ""
        quarters = page.get("quarters") or []
        if quarters:
            cards = []
            for q in quarters:
                if not isinstance(q, dict):
                    continue
                cards.append(
                    f"<div style='padding:12px 14px;border:1px solid #e0e0e0;border-radius:8px;"
                    f"background:#fff;margin:0 0 10px 0;'>"
                    f"<div style='font-weight:800;color:#1565C0;margin-bottom:6px;'>"
                    f"{ReportGenerator._escape(str(q.get('name', '')))}"
                    f"<span style='font-weight:500;color:#666;font-size:0.85rem;'>"
                    f" · {ReportGenerator._escape(str(q.get('branch', '')))}"
                    f" · {ReportGenerator._escape(str(q.get('months', '')))}</span></div>"
                    f"<p style='margin:0 0 8px 0;line-height:1.75;color:#333;'>"
                    f"{ReportGenerator._escape(str(q.get('outlook', '')))}</p>"
                    f"<div style='font-size:0.9rem;color:#555;margin-bottom:4px;'><b>{focus_l}</b>："
                    f"{ReportGenerator._escape(str(q.get('focus_months', '')))}</div>"
                    f"<div style='font-size:0.9rem;color:#555;'><b>{advice_l}</b>："
                    f"{ReportGenerator._escape(str(q.get('advice', '')))}</div>"
                    f"</div>"
                )
            season_html = (
                f"<div style='padding:14px 16px;border:1px solid #bbdefb;border-radius:10px;background:#e3f2fd;'>"
                f"<div style='font-weight:800;font-size:1.05rem;margin-bottom:12px;color:#0d47a1;'>{season_title}</div>"
                f"{''.join(cards)}</div>"
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

        qp_html = ""
        qp = plain.get("quarters_plain") or []
        if qp:
            bits = []
            for q in qp:
                if not isinstance(q, dict):
                    continue
                tips = "".join(
                    f"<li style='margin:0 0 4px 0;'>{ReportGenerator._escape(str(t))}</li>"
                    for t in (q.get("tips") or [])
                )
                bits.append(
                    f"<div style='margin:0 0 12px 0;padding:10px 12px;background:#fff;border-radius:8px;"
                    f"border:1px solid #c8e6c9;'>"
                    f"<div style='font-weight:700;color:#2e7d32;'>{ReportGenerator._escape(str(q.get('name','')))}</div>"
                    f"<div style='margin:4px 0 6px 0;line-height:1.6;'>{ReportGenerator._escape(str(q.get('summary','')))}</div>"
                    f"<ul style='margin:0;padding-left:1.2rem;'>{tips}</ul></div>"
                )
            qp_html = (
                f"<div style='font-weight:700;margin:14px 0 8px 0;'>"
                f"{season_tips}</div>{''.join(bits)}"
            )

        pro_section = ""
        if pro_blocks:
            pro_section = (
                f"<div style='padding:14px 16px;border:1px solid #e0e0e0;border-radius:10px;background:#fafafa;'>"
                f"<div style='font-weight:800;font-size:1.05rem;margin-bottom:12px;color:#424242;'>{pro_title}</div>"
                f"{''.join(pro_blocks)}</div>"
            )

        return f"""
<div style="display:flex;flex-direction:column;gap:18px;">
  <div style="font-weight:800;font-size:1.35rem;line-height:1.45;color:#1a237e;letter-spacing:0.02em;">
    {ReportGenerator._escape(str(page.get("title") or ""))}
  </div>
  {pro_section}
  {month_html}
  {season_html}
  <div style="padding:16px 18px;border:1px solid #c8e6c9;border-radius:10px;background:#f1f8f4;">
    <div style="font-weight:800;font-size:1.1rem;margin-bottom:12px;color:#2e7d32;">{plain_title}</div>
    {summary_html}
    {points_html}
    {detail_html}
    {qp_html}
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
            "max_tokens": 5200,
        }
        url = f"{self.base_url}/v1/chat/completions"
        response = requests.post(url, headers=headers, json=payload, timeout=75)
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

        # 去掉模型偶发前缀说明
        cleaned = re.sub(r"^[^{\[]+", "", cleaned, count=1).strip() or cleaned

        try:
            obj = json.loads(cleaned)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

        for candidate in (
            cleaned,
            cleaned + '"}',
            cleaned + '"]}',
            cleaned + '"]}}',
            cleaned + '"}}',
            cleaned + "}}",
            cleaned + "}]}",
        ):
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue

        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

        # 截断 JSON：尽量抽出 pageN 对象
        m = re.search(
            r'"(page\d+)"\s*:\s*\{',
            cleaned,
        )
        if m:
            key = m.group(1)
            start = cleaned.find("{", m.end() - 1)
            if start >= 0:
                depth = 0
                end = -1
                for i, ch in enumerate(cleaned[start:], start):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                blob = cleaned[start:end] if end > start else cleaned[start:]
                for cand in (blob, blob + "}", blob + '"}', blob + '"]}'):
                    try:
                        inner = json.loads(cand)
                        if isinstance(inner, dict):
                            return {key: inner}
                    except json.JSONDecodeError:
                        continue
        return {}
