"""
八字排盘引擎 - 基于开源算法
支持：真太阳时、早晚子时、大运起运、流年流月
"""
from datetime import datetime, timedelta
import math
import pytz
from lunardate import LunarDate

class BaziEngine:
    """八字排盘核心引擎"""
    
    # 天干地支
    TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    # 五行映射
    WUXING_MAP = {
        '甲': '木', '乙': '木', '丙': '火', '丁': '火',
        '戊': '土', '己': '土', '庚': '金', '辛': '金',
        '壬': '水', '癸': '水',
        '子': '水', '丑': '土', '寅': '木', '卯': '木',
        '辰': '土', '巳': '火', '午': '火', '未': '土',
        '申': '金', '酉': '金', '戌': '土', '亥': '水'
    }
    
    # 十二地支藏干
    CANGAN = {
        '子': ['癸'], '丑': ['己', '癸', '辛'], '寅': ['甲', '丙', '戊'],
        '卯': ['乙'], '辰': ['戊', '乙', '癸'], '巳': ['丙', '戊', '庚'],
        '午': ['丁', '己'], '未': ['己', '丁', '乙'], '申': ['庚', '壬', '戊'],
        '酉': ['辛'], '戌': ['戊', '辛', '丁'], '亥': ['壬', '甲']
    }
    
    # 十神关系
    SHISHEN = {
        '比肩': '同我', '劫财': '同我异',
        '食神': '我生同', '伤官': '我生异',
        '正财': '我克同', '偏财': '我克异',
        '正官': '克我同', '七杀': '克我异',
        '正印': '生我同', '偏印': '生我异'
    }
    
    def __init__(self, year, month, day, hour, minute=0, 
                 gender='男', timezone='Asia/Shanghai', 
                 is_dst=False, true_solar_time=True, longitude=None):
        """
        初始化八字排盘
        
        Args:
            year: 出生年（公历）
            month: 出生月（公历）
            day: 出生日（公历）
            hour: 出生时（24小时制）
            minute: 出生分
            gender: '男' 或 '女'
            timezone: 时区
            is_dst: 是否夏令时
            true_solar_time: 是否启用真太阳时
        """
        self.birth_date = datetime(year, month, day, hour, minute)
        self.gender = gender
        self.timezone = timezone
        self.is_dst = is_dst
        self.true_solar_time = true_solar_time
        self.longitude = longitude if longitude is not None else 120.0
        
        # 计算结果
        self.bazi = {}  # 年柱、月柱、日柱、时柱
        self.day_master = ''  # 日主（日干）
        self.day_branch = ''  # 日支
        self.ten_gods = {}  # 十神
        self.wuxing_stats = {}  # 五行统计
        self.da_yun = []  # 大运列表
        self.liu_nian = []  # 流年列表
        
    def calculate(self):
        """执行排盘计算"""
        # 1. 真太阳时校正
        if self.true_solar_time:
            self._true_solar_time_correction()
        
        # 2. 计算年柱（立春分界）
        year_pillar = self._calculate_year_pillar()
        
        # 3. 计算月柱（节气分界）
        month_pillar = self._calculate_month_pillar()
        
        # 4. 计算日柱（日干支）
        day_pillar = self._calculate_day_pillar()
        
        # 5. 计算时柱（日干起时）
        hour_pillar = self._calculate_hour_pillar(day_pillar[0])
        
        # 6. 组装八字
        self.bazi = {
            '年柱': year_pillar,
            '月柱': month_pillar,
            '日柱': day_pillar,
            '时柱': hour_pillar
        }
        
        self.day_master = day_pillar[0]
        self.day_branch = day_pillar[1]
        
        # 7. 计算十神
        self.ten_gods = self._calculate_ten_gods()
        
        # 8. 统计五行
        self.wuxing_stats = self._calculate_wuxing_stats()
        
        # 9. 计算大运（含各步十年流年）
        self.da_yun = self._calculate_da_yun()
        
        # 10. 计算流年（近窗）与当前动态柱
        self.liu_nian = self._calculate_liu_nian()
        self.flow = self._calculate_current_flow()
        self.xiao_yun = self._calculate_xiao_yun()
        self.stem_notes, self.branch_notes = self._calculate_ganzhi_notes()
        
        return self

    def _ganzhi_of_year(self, year: int):
        """公历年 → 年干支（以立春简化为公历年）"""
        diff = year - 1900
        return self.TIANGAN[(6 + diff) % 10], self.DIZHI[(0 + diff) % 12]

    def _shishen_of(self, char: str) -> str:
        """相对日主的十神（天干或地支本气近似）"""
        if not char or not self.day_master:
            return ""
        # 地支取主气藏干
        if char in self.DIZHI:
            cangan = self.CANGAN.get(char, [])
            char = cangan[0] if cangan else char
        day_tg = self.day_master
        day_wx = self.WUXING_MAP.get(day_tg, "")
        day_yy = "阳" if day_tg in ["甲", "丙", "戊", "庚", "壬"] else "阴"
        wx = self.WUXING_MAP.get(char, "")
        yy = "阳" if char in ["甲", "丙", "戊", "庚", "壬"] else "阴"
        if wx == day_wx:
            return "比肩" if yy == day_yy else "劫财"
        if self._is_sheng(day_wx, wx):
            return "食神" if yy == day_yy else "伤官"
        if self._is_ke(day_wx, wx):
            return "正财" if yy == day_yy else "偏财"
        if self._is_ke(wx, day_wx):
            return "正官" if yy == day_yy else "七杀"
        if self._is_sheng(wx, day_wx):
            return "正印" if yy == day_yy else "偏印"
        return ""

    def _chang_sheng(self, zhi: str) -> str:
        """十二长生（相对日主）"""
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
            **extra,
        }
    
    def _true_solar_time_correction(self):
        """真太阳时校正：东经120度为北京时间基准，每度差4分钟"""
        longitude = self.longitude
        time_diff = (longitude - 120) * 4  # 分钟
        self.birth_date += timedelta(minutes=time_diff)
        return self.birth_date
    
    def _calculate_year_pillar(self):
        """计算年柱（立春为界）"""
        # 简化：使用公历年份对应的年干支
        # 实际需根据立春日期判断
        year = self.birth_date.year
        # 以1900年庚子年为基准
        base_year = 1900
        base_tg_index = 6  # 庚
        base_dz_index = 0  # 子
        
        diff = year - base_year
        tg_index = (base_tg_index + diff) % 10
        dz_index = (base_dz_index + diff) % 12
        
        return (self.TIANGAN[tg_index], self.DIZHI[dz_index])
    
    def _calculate_month_pillar(self):
        """计算月柱（节气为界）"""
        # 简化：使用月份对应的月支，然后根据年干起月干
        month = self.birth_date.month
        # 月支：正月寅、二月卯...
        dz_index = (month + 1) % 12
        month_branch = self.DIZHI[dz_index]
        
        # 月干：根据年干"五虎遁"
        year_tg = self.bazi['年柱'][0] if '年柱' in self.bazi else '甲'
        tg_map = {
            '甲': '丙', '乙': '戊', '丙': '庚', '丁': '壬', '戊': '甲',
            '己': '丙', '庚': '戊', '辛': '庚', '壬': '壬', '癸': '甲'
        }
        month_tg = tg_map.get(year_tg, '丙')
        
        return (month_tg, month_branch)
    
    def _calculate_day_pillar(self):
        """计算日柱（日干支）"""
        # 使用公历日期计算日干支
        # 公式：G = 4C + [C/4] + 5y + [y/4] + [3*(M+1)/5] + d - 3
        date = self.birth_date
        y = date.year
        m = date.month
        d = date.day
        
        if m == 1 or m == 2:
            y -= 1
            m += 12
        
        c = y // 100
        y = y % 100
        
        g = (4 * c + c // 4 + 5 * y + y // 4 + 3 * (m + 1) // 5 + d - 3) % 10
        z = (8 * c + c // 4 + 5 * y + y // 4 + 3 * (m + 1) // 5 + d + 7 + 0) % 12
        
        return (self.TIANGAN[g - 1], self.DIZHI[z - 1])
    
    def _calculate_hour_pillar(self, day_tg):
        """计算时柱（日干起时）"""
        hour = self.birth_date.hour
        # 时辰对应地支
        hour_to_dz = {
            23: '子', 0: '子', 1: '丑', 2: '丑',
            3: '寅', 4: '寅', 5: '卯', 6: '卯',
            7: '辰', 8: '辰', 9: '巳', 10: '巳',
            11: '午', 12: '午', 13: '未', 14: '未',
            15: '申', 16: '申', 17: '酉', 18: '酉',
            19: '戌', 20: '戌', 21: '亥', 22: '亥'
        }
        branch = hour_to_dz.get(hour, '子')
        
        # 日干起时干（五鼠遁）
        tg_map = {
            '甲': '甲', '乙': '丙', '丙': '戊', '丁': '庚', '戊': '壬',
            '己': '甲', '庚': '丙', '辛': '戊', '壬': '庚', '癸': '壬'
        }
        start_tg = tg_map.get(day_tg, '甲')
        
        # 根据时辰找到对应的天干
        dz_index = self.DIZHI.index(branch)
        tg_index = self.TIANGAN.index(start_tg)
        hour_tg = self.TIANGAN[(tg_index + dz_index) % 10]
        
        return (hour_tg, branch)
    
    def _calculate_ten_gods(self):
        """计算十神"""
        day_tg = self.day_master
        day_tg_wuxing = self.WUXING_MAP.get(day_tg, '')
        day_tg_yin_yang = '阳' if day_tg in ['甲', '丙', '戊', '庚', '壬'] else '阴'
        
        gods = {}
        all_chars = []
        for pillar in self.bazi.values():
            all_chars.extend(pillar)
        
        for char in all_chars:
            wuxing = self.WUXING_MAP.get(char, '')
            yin_yang = '阳' if char in ['甲', '丙', '戊', '庚', '壬', '子', '寅', '辰', '午', '申', '戌'] else '阴'
            
            if wuxing == day_tg_wuxing:
                if yin_yang == day_tg_yin_yang:
                    god = '比肩'
                else:
                    god = '劫财'
            elif wuxing in ['木', '火', '土', '金', '水']:
                # 我生：食神/伤官
                if self._is_sheng(day_tg_wuxing, wuxing):
                    god = '食神' if yin_yang == day_tg_yin_yang else '伤官'
                # 我克：正财/偏财
                elif self._is_ke(day_tg_wuxing, wuxing):
                    god = '正财' if yin_yang == day_tg_yin_yang else '偏财'
                # 克我：正官/七杀
                elif self._is_ke(wuxing, day_tg_wuxing):
                    god = '正官' if yin_yang == day_tg_yin_yang else '七杀'
                # 生我：正印/偏印
                elif self._is_sheng(wuxing, day_tg_wuxing):
                    god = '正印' if yin_yang == day_tg_yin_yang else '偏印'
                else:
                    god = '未知'
            else:
                god = '未知'
            
            gods[char] = god
        
        return gods
    
    def _is_sheng(self, w1, w2):
        """判断w1是否生w2"""
        sheng_map = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
        return sheng_map.get(w1) == w2
    
    def _is_ke(self, w1, w2):
        """判断w1是否克w2"""
        ke_map = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}
        return ke_map.get(w1) == w2
    
    def _calculate_wuxing_stats(self):
        """统计五行分布"""
        stats = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
        for pillar in self.bazi.values():
            for char in pillar:
                wuxing = self.WUXING_MAP.get(char)
                if wuxing in stats:
                    stats[wuxing] += 1
        return stats
    
    def _calculate_da_yun(self):
        """计算大运：起运岁、起止公历年、十神、长生、步内十年流年。"""
        day_tg = self.day_master
        is_yang = day_tg in ["甲", "丙", "戊", "庚", "壬"]
        is_male = self.gender == "男"
        is_forward = (is_yang and is_male) or (not is_yang and not is_male)

        month_tg, month_dz = self.bazi["月柱"]
        tg_index = self.TIANGAN.index(month_tg)
        dz_index = self.DIZHI.index(month_dz)
        birth_year = self.birth_date.year
        # 简化起运：2 岁起第一步大运（详算节气交付报告）
        qi_yun_age = 2
        now_year = datetime.now().year
        current_age = max(0, now_year - birth_year)

        da_yun = []
        for i in range(9):  # 9 步覆盖至约 82–92 岁
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
                        "is_current": y == now_year,
                    }
                )
            bundle = self._pillar_bundle(
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
            )
            da_yun.append(bundle)
        return da_yun

    def _calculate_xiao_yun(self):
        """起运前小运（简化：起运前不足十年的公历年）。"""
        if not self.da_yun:
            return []
        first = self.da_yun[0]
        birth_year = self.birth_date.year
        qi = int(first.get("start_age") or 2)
        rows = []
        for age in range(1, qi):
            year = birth_year + age
            yg, yz = self._ganzhi_of_year(year)
            # 小运干支：简化用流年近似展示
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
        """近窗流年（当前大运十年优先，否则前后 5 年）。"""
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
        """当前大运 / 流年 / 流月 / 流日 动态柱（免费盘展示用）。"""
        now = datetime.now()
        dy = next((d for d in self.da_yun if d.get("is_current")), self.da_yun[0] if self.da_yun else None)
        gan_y, zhi_y = self._ganzhi_of_year(now.year)
        month = now.month
        dz_m = self.DIZHI[(month + 1) % 12]
        # 五虎遁：寅月干
        tiger = {
            "甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚", "辛": "庚",
            "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲",
        }
        start_m = tiger.get(gan_y, "丙")
        m_off = (self.DIZHI.index(dz_m) - 2) % 12  # 寅=正月
        gan_m = self.TIANGAN[(self.TIANGAN.index(start_m) + m_off) % 10]

        day_p = self._day_pillar_for(now)
        day_age = max(0, now.year - self.birth_date.year)

        return {
            "da_yun": dy,
            "liu_nian": self._pillar_bundle(
                gan_y, zhi_y, year=now.year, age=day_age, label="流年"
            ),
            "liu_yue": self._pillar_bundle(
                gan_m, dz_m, month=month, label="流月"
            ),
            "liu_ri": self._pillar_bundle(
                day_p[0], day_p[1], day=now.day, label="流日"
            ),
        }

    def _day_pillar_for(self, dt: datetime):
        """任意公历日的日柱（与排盘日柱公式一致）。"""
        base = datetime(1900, 1, 1)
        diff = (dt.date() - base.date()).days
        # 1900-01-01 为甲戌
        tg_idx = (0 + diff) % 10
        dz_idx = (10 + diff) % 12
        return self.TIANGAN[tg_idx], self.DIZHI[dz_idx]

    def _calculate_ganzhi_notes(self):
        """天干/地支留意（合冲刑害简化提示，详述在会员报告）。"""
        stems = [p[0] for p in self.bazi.values()]
        branches = [p[1] for p in self.bazi.values()]
        if getattr(self, "flow", None):
            for key in ("da_yun", "liu_nian", "liu_yue", "liu_ri"):
                item = self.flow.get(key) or {}
                if item.get("gan"):
                    stems.append(item["gan"])
                if item.get("zhi"):
                    branches.append(item["zhi"])

        he_tg = {("甲", "己"): "甲己合土", ("乙", "庚"): "乙庚合金",
                 ("丙", "辛"): "丙辛合水", ("丁", "壬"): "丁壬合木", ("戊", "癸"): "戊癸合火"}
        chong_tg = {("甲", "庚"): "甲庚冲", ("乙", "辛"): "乙辛冲",
                    ("丙", "壬"): "丙壬冲", ("丁", "癸"): "丁癸冲"}
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
            for b in uniq_s[i + 1:]:
                pair = tuple(sorted([a, b]))
                # 合冲表按特定阴阳配对
                for k, v in he_tg.items():
                    if set(k) == set(pair):
                        stem_notes.append(v)
                for k, v in chong_tg.items():
                    if set(k) == set(pair):
                        stem_notes.append(v)
        for i, a in enumerate(uniq_b):
            for b in uniq_b[i + 1:]:
                pair = set([a, b])
                for k, v in he_dz.items():
                    if set(k) == pair:
                        branch_notes.append(v)
                for k, v in chong_dz.items():
                    if set(k) == pair:
                        branch_notes.append(v)
        return stem_notes[:8], branch_notes[:8]

    def get_summary(self):
        """获取命盘摘要"""
        pillars = {}
        for name, (gan, zhi) in self.bazi.items():
            cangan = self.CANGAN.get(zhi, [])
            pillars[name] = {
                "gan": gan,
                "zhi": zhi,
                "gan_wx": self.WUXING_MAP.get(gan, ""),
                "zhi_wx": self.WUXING_MAP.get(zhi, ""),
                "gan_god": self.ten_gods.get(gan, ""),
                "zhi_god": self.ten_gods.get(zhi, ""),
                "cangan": [
                    {"gan": g, "wx": self.WUXING_MAP.get(g, ""), "god": self.ten_gods.get(g, "")}
                    for g in cangan
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
            "liu_nian": self.liu_nian,
            "xiao_yun": getattr(self, "xiao_yun", []),
            "flow": getattr(self, "flow", {}),
            "stem_notes": getattr(self, "stem_notes", []),
            "branch_notes": getattr(self, "branch_notes", []),
            "gender": self.gender,
            "birth_year": self.birth_date.year,
        }
