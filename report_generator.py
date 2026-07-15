"""
八页报告生成器 - 使用DeepSeek API
"""
import json
import requests
from datetime import datetime

class ReportGenerator:
    """生成八页命理报告"""
    
    def __init__(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
    def generate(self, bazi_data, birth_info, payment_tier='monthly'):
        """
        生成完整八页报告
        
        Args:
            bazi_data: 八字排盘数据
            birth_info: 出生信息（姓名、性别、出生时间等）
            payment_tier: 'monthly' 或 'quarterly'
        
        Returns:
            dict: 八页报告内容
        """
        # 构建提示词
        prompt = self._build_prompt(bazi_data, birth_info)
        
        # 调用DeepSeek API
        response = self._call_deepseek(prompt)
        
        # 解析返回的JSON
        report = self._parse_response(response)
        
        return report
    
    def _build_prompt(self, bazi_data, birth_info):
        """构建系统提示词"""
        
        # 提取关键数据
        bazi = bazi_data['bazi']
        day_master = bazi_data['day_master']
        wuxing_stats = bazi_data['wuxing_stats']
        da_yun = bazi_data['da_yun']
        liu_nian = bazi_data['liu_nian']
        gender = bazi_data['gender']
        
        # 当前大运和流年
        current_da_yun = da_yun[0] if da_yun else None
        current_liu_nian = next((n for n in liu_nian if n['is_current']), liu_nian[-1] if liu_nian else None)
        
        prompt = f"""
你是一位专业的命理大师，精通八字命理学、五行生克、大运流年推断。请根据以下命盘数据，生成一份详细的八页命理报告。

## 命盘数据
- 姓名：{birth_info.get('name', '用户')}
- 性别：{gender}
- 出生时间：{birth_info.get('birth_date', '')}
- 八字：年柱 {bazi['年柱'][0]}{bazi['年柱'][1]}，月柱 {bazi['月柱'][0]}{bazi['月柱'][1]}，日柱 {bazi['日柱'][0]}{bazi['日柱'][1]}，时柱 {bazi['时柱'][0]}{bazi['时柱'][1]}
- 日主：{day_master}
- 五行分布：{json.dumps(wuxing_stats, ensure_ascii=False)}
- 当前大运：第{current_da_yun['step']}步，{current_da_yun['gan']}{current_da_yun['zhi']}，{current_da_yun['years']}
- 当前流年：{current_liu_nian['year']}年 {current_liu_nian['gan']}{current_liu_nian['zhi']}

## 报告要求
请生成一份完整的八页报告，严格按以下结构输出为JSON格式：

### 页一：八字命盘与基本信息
- 四柱八字（年、月、日、时）
- 十神分析（日主与各柱的关系）
- 五行旺衰（各五行数量与强弱）
- 大运走势（当前大运及下一大运开始时间）
- 建议：知进退、未雨绸缪

### 页二：事业流年详批 (Part 1)
- 当年事业整体运势
- 可能发生的大事（升职、跳槽、项目成败等）
- 需注意事项（小人、贵人、竞争等）
- 关键时间节点（哪个月份最有利/最需谨慎）

### 页三：事业流年详批 (Part 2)
- 命格事业特质分析
- 适合发展的五行方向（如：木火行业、金水行业）
- 职业建议（适合的岗位、行业转换时机）
- 发展策略建议

### 页四：财运流年详批 (Part 1)
- 当年财运整体趋势
- 是否适合投资投机（股票、房产、创业等）
- 财富最强势的时间段
- 需要谨慎的月份
- 今年是破财还是得财？得财方向是什么？

### 页五：财运流年详批 (Part 2)
- 资产配置五行方向建议（木火资产、金水资产等）
- 适合的理财方式
- 投资风险提示
- 财富积累策略

### 页六：感情流年详批 (Part 1)
- 当年感情运势整体发展
- 可能的感情事件（拍拖、分手、结婚、离婚、吵架、第三者、异地恋等）
- 桃花运分析（桃花星、桃花月）
- 感情注意事项

### 页七：感情流年详批 (Part 2)
- 命中适合的感情风水布局建议
- 提升感情运势的方法
- 适合的另一半八字特征
- 感情发展时机建议

### 页八：健康流年详批
- 当年整体健康状况
- 需注意的重大疾病风险（根据五行对应五脏：木→肝、火→心、土→脾、金→肺、水→肾）
- 容易生病的时段（哪个月份）
- 哪类疾病最容易中招
- 就医建议（找什么类型的医生、哪方向医院更有利）

## 输出格式
必须输出为严格的JSON格式，结构如下：
{{
  "page1": {{"title": "八字命盘与基本信息", "content": "..."}},
  "page2": {{"title": "事业流年详批 (Part 1)", "content": "..."}},
  "page3": {{"title": "事业流年详批 (Part 2)", "content": "..."}},
  "page4": {{"title": "财运流年详批 (Part 1)", "content": "..."}},
  "page5": {{"title": "财运流年详批 (Part 2)", "content": "..."}},
  "page6": {{"title": "感情流年详批 (Part 1)", "content": "..."}},
  "page7": {{"title": "感情流年详批 (Part 2)", "content": "..."}},
  "page8": {{"title": "健康流年详批", "content": "..."}}
}}

请确保内容专业、详细、有针对性，避免泛泛而谈。每个页面的content至少500字。
"""
        return prompt
    
    def _call_deepseek(self, prompt):
        """调用DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一位专业命理大师，擅长八字分析。请根据提供的数据生成详细报告，仅输出JSON格式。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"DeepSeek API错误: {response.status_code} - {response.text}")
    
    def _parse_response(self, response_text):
        """解析DeepSeek返回的JSON"""
        try:
            # 尝试提取JSON（可能被markdown包裹）
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            elif '```' in response_text:
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            
            report = json.loads(response_text)
            
            # 确保所有页面都存在
            pages = ['page1', 'page2', 'page3', 'page4', 'page5', 'page6', 'page7', 'page8']
            for page in pages:
                if page not in report:
                    report[page] = {
                        'title': f'第{int(page[4])}页',
                        'content': '报告生成中，请稍后查看完整版本。'
                    }
            
            return report
            
        except json.JSONDecodeError as e:
            # 如果解析失败，返回一个基本报告
            return {
                'page1': {'title': '八字命盘与基本信息', 'content': f'排盘数据：{response_text[:200]}...\n\n（报告生成中，请重试）'}
            }
