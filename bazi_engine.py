"""
八字排盘引擎
- 年柱：立春分界
- 月柱：节令分界 + 五虎遁
- 日柱：统一用 1900-01-01=甲戌 纪日
- 时柱：五鼠遁
- 十神：正=阴阳异，偏=阴阳同（食神同/伤官异）
"""
from datetime import datetime, timedelta

from solar_terms import lichun, month_branch_by_jieqi, qi_yun_from_jieqi
from bazi_meta import (
    cheng_gu,
    day_kongwang,
    nayin_of,
    shensha_for_chart,
)

class BaziEngine:
    """八字排盘核心引擎"""

    TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    WUXING_MAP = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火",
        "戊": "土", "己": "土", "庚": "金", "辛": "金",
        "壬": "水", "癸": "水",
        "子": "水", "丑": "土", "寅": "木", "卯": "木",
        "辰": "土", "巳": "火", "午": "火", "未": "土",
        "申": "金", "酉": "金", "戌": "土", "亥": "水",
    }

    # 十二地支藏干：本气 → 中气 → 余气（《渊海子平》通行表）
    CANGAN = {
        "子": ["癸"],
        "丑": ["己", "癸", "辛"],
        "寅": ["甲", "丙", "戊"],
        "卯": ["乙"],
        "辰": ["戊", "乙", "癸"],
        "巳": ["丙", "戊", "庚"],
        "午": ["丁", "己"],
        "未": ["己", "丁", "乙"],
        "申": ["庚", "壬", "戊"],
        "酉": ["辛"],
        "戌": ["戊", "辛", "丁"],
        "亥": ["壬", "甲"],
    }
    CANGAN_ROLE = ("本气", "中气", "余气")

    YANG_GAN = {"甲", "丙", "戊", "庚", "壬"}

    def __init__(
        self,
        year,
        month,
        day,
        hour,
        minute=0,
        gender="男",
        timezone="Asia/Shanghai",
        is_dst=False,
        true_solar_time=True,
        longitude=None,
    ):
        self.raw_birth = datetime(year, month, day, hour, minute)
        self.birth_date = self.raw_birth
        self.gender = gender
        self.timezone = timezone
        self.is_dst = is_dst
        self.true_solar_time = true_solar_time
        self.longitude = longitude if longitude is not None else 120.0

        self.bazi = {}
        self.day_master = ""
        self.day_branch = ""
        self.ten_gods = {}
        self.wuxing_stats = {}
        self.da_yun = []
        self.liu_nian = []
        self.meta = {}

    def calculate(self):
        if self.true_solar_time:
            self._true_solar_time_correction()

        year_pillar = self._calculate_year_pillar()
        self.bazi = {"年柱": year_pillar}
        month_pillar = self._calculate_month_pillar()
        day_pillar = self._calculate_day_pillar()
        hour_pillar = self._calculate_hour_pillar(day_pillar[0])

        self.bazi = {
            "年柱": year_pillar,
            "月柱": month_pillar,
            "日柱": day_pillar,
            "时柱": hour_pillar,
        }
        self.day_master = day_pillar[0]
        self.day_branch = day_pillar[1]
        self.ten_gods = self._calculate_ten_gods()
        self.wuxing_stats = self._calculate_wuxing_stats()
        self.da_yun = self._calculate_da_yun()
        self.liu_nian = self._calculate_liu_nian()
        self.flow = self._calculate_current_flow()
        self.xiao_yun = self._calculate_xiao_yun()
        self.stem_notes, self.branch_notes = self._calculate_ganzhi_notes()
        self.meta = self._build_meta()
        return self

    def _build_meta(self) -> dict:
        pillars = self.bazi
        nayin = {name: nayin_of(g, z) for name, (g, z) in pillars.items()}
        kw = day_kongwang(self.day_master, self.day_branch)
        lunar_month = self.raw_birth.month
        lunar_day = self.raw_birth.day
        try:
            from lunardate import LunarDate

            ld = LunarDate.fromSolarDate(
                self.raw_birth.year, self.raw_birth.month, self.raw_birth.day
            )
            lunar_month, lunar_day = ld.month, ld.day
            lunar_note = "农历"
        except Exception:
            lunar_note = "公历近似"
        year_gz = f"{pillars['年柱'][0]}{pillars['年柱'][1]}"
        cg = cheng_gu(year_gz, lunar_month, lunar_day, pillars["时柱"][1])
        cg["calendar_note"] = lunar_note
        shensha = shensha_for_chart(
            self.day_master,
            self.day_branch,
            pillars["年柱"][1],
            pillars["月柱"][1],
            pillars,
        )
        kong_flags = {name: (zhi in kw) for name, (_g, zhi) in pillars.items()}
        return {
            "nayin": nayin,
            "kongwang": kw,
            "kongwang_text": "".join(kw) if kw else "",
            "kong_flags": kong_flags,
            "shensha": shensha,
            "cheng_gu": cg,
        }

    def _ganzhi_of_year(self, year: int):
        diff = year - 1900
        return self.TIANGAN[(6 + diff) % 10], self.DIZHI[(0 + diff) % 12]

    def _yy(self, char: str) -> str:
        if char in self.YANG_GAN:
            return "阳"
        if char in self.TIANGAN:
            return "阴"
        return "阳" if char in ["子", "寅", "辰", "午", "申", "戌"] else "阴"

    def _shishen_of(self, char: str) -> str:
        if not char or not self.day_master:
            return ""
        if char in self.DIZHI:
            cangan = self.CANGAN.get(char, [])
            char = cangan[0] if cangan else char
        day_tg = self.day_master
        day_wx = self.WUXING_MAP.get(day_tg, "")
        day_yy = self._yy(day_tg)
        wx = self.WUXING_MAP.get(char, "")
        yy = self._yy(char)
        same = yy == day_yy
        if wx == day_wx:
            return "比肩" if same else "劫财"
        if self._is_sheng(day_wx, wx):
            return "食神" if same else "伤官"
        if self._is_ke(day_wx, wx):
            return "偏财" if same else "正财"
        if self._is_ke(wx, day_wx):
            return "七杀" if same else "正官"
        if self._is_sheng(wx, day_wx):
            return "偏印" if same else "正印"
        return ""

    def _chang_sheng(self, zhi: str) -> str:
        order = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]
        yang_start = {"甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申"}
        yin_start = {"乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯"}
        dm = self.day_master
        is_yang = dm in yang_start
        start = yang_start.get(dm) or yin_start.get(dm)
        if not start or zhi not in self.DIZHI:
            return ""
        start_i = self.DIZHI.index(start)
        zhi_i = self.DIZHI.index(zhi)
        if is_yang:
            idx = (zhi_i - start_i) % 12
        else:
            idx = (start_i - zhi_i) % 12
        return order[idx]

    def _pillar_bundle(self, gan: str, zhi: str, **extra) -> dict:
        cangan = self.CANGAN.get(zhi, [])
        return {
            "gan": gan,
            "zhi": zhi,
            "gan_wx": self.WUXING_MAP.get(gan, ""),
            "zhi_wx": self.WUXING_MAP.get(zhi, ""),
            "gan_god": self._shishen_of(gan),
            "zhi_gods": [self._shishen_of(g) for g in cangan],
            "cangan": cangan,
            "chang_sheng": self._chang_sheng(zhi),
            "nayin": nayin_of(gan, zhi),
            **extra,
        }

    def _true_solar_time_correction(self):
        time_diff = (self.longitude - 120) * 4
        self.birth_date = self.raw_birth + timedelta(minutes=time_diff)
        return self.birth_date

    def _calculate_year_pillar(self):
        dt = self.birth_date
        y = dt.year
        if dt < lichun(y):
            y -= 1
        diff = y - 1900
        return self.TIANGAN[(6 + diff) % 10], self.DIZHI[(0 + diff) % 12]

    def _calculate_month_pillar(self):
        month_branch, jie_name = month_branch_by_jieqi(self.birth_date)
        self._month_jie = jie_name
        year_tg = self.bazi["年柱"][0]
        tiger = {
            "甲": "丙", "己": "丙",
            "乙": "戊", "庚": "戊",
            "丙": "庚", "辛": "庚",
            "丁": "壬", "壬": "壬",
            "戊": "甲", "癸": "甲",
        }
        start = tiger.get(year_tg, "丙")
        off = (self.DIZHI.index(month_branch) - 2) % 12
        month_tg = self.TIANGAN[(self.TIANGAN.index(start) + off) % 10]
        return (month_tg, month_branch)

    def _calculate_day_pillar(self):
        return self._day_pillar_for(self.birth_date)

    def _calculate_hour_pillar(self, day_tg):
        hour = self.birth_date.hour
        minute = self.birth_date.minute
        total_min = hour * 60 + minute
        if total_min >= 23 * 60 or total_min < 60:
            branch = "子"
        else:
            idx = ((hour + 1) // 2) % 12
            branch = self.DIZHI[idx]

        tg_map = {
            "甲": "甲", "乙": "丙", "丙": "戊", "丁": "庚", "戊": "壬",
            "己": "甲", "庚": "丙", "辛": "戊", "壬": "庚", "癸": "壬",
        }
        start_tg = tg_map.get(day_tg, "甲")
        dz_index = self.DIZHI.index(branch)
        tg_index = self.TIANGAN.index(start_tg)
        hour_tg = self.TIANGAN[(tg_index + dz_index) % 10]
        return (hour_tg, branch)

    def _calculate_ten_gods(self):
        gods = {}
        for gan, zhi in self.bazi.values():
            gods[gan] = self._shishen_of(gan)
            gods[zhi] = self._shishen_of(zhi)
            for g in self.CANGAN.get(zhi, []):
                gods[g] = self._shishen_of(g)
        gods[self.day_master] = "日主"
        return gods

    def _is_sheng(self, w1, w2):
        return {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}.get(w1) == w2

    def _is_ke(self, w1, w2):
        return {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}.get(w1) == w2

    def _calculate_wuxing_stats(self):
        stats = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for gan, zhi in self.bazi.values():
            for char in (gan, zhi):
                wx = self.WUXING_MAP.get(char)
                if wx in stats:
                    stats[wx] += 1
            cang = self.CANGAN.get(zhi, [])
            if cang:
                wx = self.WUXING_MAP.get(cang[0])
                if wx in stats:
                    stats[wx] += 1
        return stats

    def _calculate_da_yun(self):
        """大运：以年干阴阳+性别定顺逆；起运按交节三天折一年。"""
        year_tg = self.bazi["年柱"][0]
        year_yang = year_tg in self.YANG_GAN
        is_male = self.gender == "男"
        # 阳男阴女顺，阴男阳女逆（专以年干）
        is_forward = (year_yang and is_male) or ((not year_yang) and (not is_male))

        qy = qi_yun_from_jieqi(self.birth_date, is_forward)
        self.qi_yun_info = qy
        qi_yun_age = int(qy.get("start_age") or 1)

        month_tg, month_dz = self.bazi["月柱"]
        tg_index = self.TIANGAN.index(month_tg)
        dz_index = self.DIZHI.index(month_dz)
        birth_year = self.raw_birth.year
        now = datetime.now()
        # 虚岁：年差 + 1（与大运步龄标注一致）
        current_age = max(1, now.year - birth_year + 1)

        da_yun = []
        for i in range(9):
            if is_forward:
                tg_idx = (tg_index + i + 1) % 10
                dz_idx = (dz_index + i + 1) % 12
            else:
                tg_idx = (tg_index - i - 1) % 10
                dz_idx = (dz_index - i - 1) % 12
            gan, zhi = self.TIANGAN[tg_idx], self.DIZHI[dz_idx]
            start_age = qi_yun_age + i * 10
            end_age = start_age + 9
            start_year = birth_year + start_age
            end_year = start_year + 9
            years_ln = []
            for y in range(start_year, end_year + 1):
                yg, yz = self._ganzhi_of_year(y)
                years_ln.append(
                    {
                        "year": y,
                        "gan": yg,
                        "zhi": yz,
                        "gan_god": self._shishen_of(yg),
                        "is_current": y == now.year,
                    }
                )
            da_yun.append(
                self._pillar_bundle(
                    gan,
                    zhi,
                    step=i + 1,
                    start_age=start_age,
                    end_age=end_age,
                    start_year=start_year,
                    end_year=end_year,
                    years=f"{start_age:02d}-{end_age:02d}岁",
                    age_label=f"{start_age:02d}岁",
                    liu_nian=years_ln,
                    is_current=start_age <= current_age <= end_age,
                    direction="顺" if is_forward else "逆",
                    qi_yun_label=qy.get("age_label", ""),
                )
            )
        return da_yun

    def _calculate_xiao_yun(self):
        if not self.da_yun:
            return []
        first = self.da_yun[0]
        birth_year = self.raw_birth.year
        qi = int(first.get("start_age") or 2)
        rows = []
        for age in range(1, qi):
            year = birth_year + age
            yg, yz = self._ganzhi_of_year(year)
            rows.append(
                {
                    "age": age,
                    "year": year,
                    "gan": yg,
                    "zhi": yz,
                    "gan_god": self._shishen_of(yg),
                    "liu_nian": f"{yg}{yz}",
                }
            )
        return rows

    def _calculate_liu_nian(self):
        now_year = datetime.now().year
        current_dy = next((d for d in self.da_yun if d.get("is_current")), None)
        if current_dy and current_dy.get("liu_nian"):
            return list(current_dy["liu_nian"])
        out = []
        for year in range(now_year - 5, now_year + 6):
            gan, zhi = self._ganzhi_of_year(year)
            out.append(
                {
                    "year": year,
                    "gan": gan,
                    "zhi": zhi,
                    "gan_god": self._shishen_of(gan),
                    "is_current": year == now_year,
                }
            )
        return out

    def _calculate_current_flow(self):
        now = datetime.now()
        # 与排盘一致：可选经度平太阳时校正（影响子时边界）
        if self.true_solar_time:
            now = now + timedelta(minutes=(self.longitude - 120) * 4)

        dy = next((d for d in self.da_yun if d.get("is_current")), self.da_yun[0] if self.da_yun else None)

        # 流年：立春换年
        y = now.year
        if now < lichun(y):
            y -= 1
        gan_y, zhi_y = self._ganzhi_of_year(y)

        dz_m, _ = month_branch_by_jieqi(now)
        tiger = {
            "甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚", "辛": "庚",
            "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲",
        }
        start_m = tiger.get(gan_y, "丙")
        m_off = (self.DIZHI.index(dz_m) - 2) % 12
        gan_m = self.TIANGAN[(self.TIANGAN.index(start_m) + m_off) % 10]

        # 流日：子时（23:00）起换日 —— 与命理排盘惯例一致
        day_p = self._day_pillar_for(now)
        day_age = max(1, now.year - self.raw_birth.year + 1)
        return {
            "da_yun": dy,
            "liu_nian": self._pillar_bundle(gan_y, zhi_y, year=y, age=day_age, label="流年"),
            "liu_yue": self._pillar_bundle(gan_m, dz_m, month=now.month, label="流月"),
            "liu_ri": self._pillar_bundle(
                day_p[0], day_p[1], day=now.day, label="流日"
            ),
        }

    def _day_pillar_for(self, dt: datetime):
        """日柱：1900-01-01=甲戌；23:00 起算次日（子时换日）。"""
        if getattr(dt, "hour", 0) >= 23:
            dt = dt + timedelta(days=1)
        base = datetime(1900, 1, 1)
        diff = (dt.date() - base.date()).days
        tg_idx = (0 + diff) % 10
        dz_idx = (10 + diff) % 12
        return self.TIANGAN[tg_idx], self.DIZHI[dz_idx]

    def _calculate_ganzhi_notes(self):
        stems = [p[0] for p in self.bazi.values()]
        branches = [p[1] for p in self.bazi.values()]
        if getattr(self, "flow", None):
            for key in ("da_yun", "liu_nian", "liu_yue", "liu_ri"):
                item = self.flow.get(key) or {}
                if item.get("gan"):
                    stems.append(item["gan"])
                if item.get("zhi"):
                    branches.append(item["zhi"])

        he_tg = {
            ("甲", "己"): "甲己合土", ("乙", "庚"): "乙庚合金",
            ("丙", "辛"): "丙辛合水", ("丁", "壬"): "丁壬合木", ("戊", "癸"): "戊癸合火",
        }
        chong_tg = {
            ("甲", "庚"): "甲庚冲", ("乙", "辛"): "乙辛冲",
            ("丙", "壬"): "丙壬冲", ("丁", "癸"): "丁癸冲",
        }
        he_dz = {
            ("子", "丑"): "子丑合土", ("寅", "亥"): "寅亥合木", ("卯", "戌"): "卯戌合火",
            ("辰", "酉"): "辰酉合金", ("巳", "申"): "巳申合水", ("午", "未"): "午未合土",
        }
        chong_dz = {
            ("子", "午"): "子午冲", ("丑", "未"): "丑未冲", ("寅", "申"): "寅申冲",
            ("卯", "酉"): "卯酉冲", ("辰", "戌"): "辰戌冲", ("巳", "亥"): "巳亥冲",
        }
        stem_notes, branch_notes = [], []
        uniq_s, uniq_b = list(dict.fromkeys(stems)), list(dict.fromkeys(branches))
        for i, a in enumerate(uniq_s):
            for b in uniq_s[i + 1 :]:
                pair = set([a, b])
                for k, v in he_tg.items():
                    if set(k) == pair:
                        stem_notes.append(v)
                for k, v in chong_tg.items():
                    if set(k) == pair:
                        stem_notes.append(v)
        for i, a in enumerate(uniq_b):
            for b in uniq_b[i + 1 :]:
                pair = set([a, b])
                for k, v in he_dz.items():
                    if set(k) == pair:
                        branch_notes.append(v)
                for k, v in chong_dz.items():
                    if set(k) == pair:
                        branch_notes.append(v)
        return stem_notes[:8], branch_notes[:8]

    def get_summary(self):
        pillars = {}
        meta = getattr(self, "meta", {}) or {}
        nayin = meta.get("nayin") or {}
        shensha = meta.get("shensha") or {}
        kong_flags = meta.get("kong_flags") or {}
        for name, (gan, zhi) in self.bazi.items():
            cangan = self.CANGAN.get(zhi, [])
            pillars[name] = {
                "gan": gan,
                "zhi": zhi,
                "gan_wx": self.WUXING_MAP.get(gan, ""),
                "zhi_wx": self.WUXING_MAP.get(zhi, ""),
                "gan_god": "日主" if name == "日柱" else self._shishen_of(gan),
                "zhi_god": self._shishen_of(zhi),
                "nayin": nayin.get(name, nayin_of(gan, zhi)),
                "shensha": shensha.get(name, []),
                "is_kong": bool(kong_flags.get(name)),
                "chang_sheng": self._chang_sheng(zhi),
                "cangan": [
                    {
                        "gan": g,
                        "wx": self.WUXING_MAP.get(g, ""),
                        "god": self._shishen_of(g),
                        "role": self.CANGAN_ROLE[i] if i < len(self.CANGAN_ROLE) else "",
                    }
                    for i, g in enumerate(cangan)
                ],
            }
        return {
            "bazi": self.bazi,
            "pillars": pillars,
            "day_master": self.day_master,
            "day_branch": self.day_branch,
            "ten_gods": self.ten_gods,
            "wuxing_stats": self.wuxing_stats,
            "da_yun": self.da_yun,
            "qi_yun": getattr(self, "qi_yun_info", {}),
            "liu_nian": self.liu_nian,
            "xiao_yun": getattr(self, "xiao_yun", []),
            "flow": getattr(self, "flow", {}),
            "stem_notes": getattr(self, "stem_notes", []),
            "branch_notes": getattr(self, "branch_notes", []),
            "meta": meta,
            "gender": self.gender,
            "birth_year": self.raw_birth.year,
            "birth_adjusted": self.birth_date.isoformat(sep=" ", timespec="minutes"),
            "month_jie": getattr(self, "_month_jie", ""),
        }
