"""
Supabase数据库客户端 - 多App隔离版本
"""
from supabase import create_client, Client
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

class SupabaseClient:
    """支持多App隔离的Supabase客户端"""
    
    APP_ID = "sigma_fate_v1"
    SCHEMA = "app_sigma_fate"
    
    def __init__(self, url: str, key: str, use_service_role: bool = False):
        """
        初始化客户端
        
        Args:
            url: Supabase URL
            key: API Key (anon 或 service_role)
            use_service_role: 是否使用服务角色（绕过RLS）
        """
        self.client: Client = create_client(url, key)
        self.use_service_role = use_service_role
        
    def _get_table(self, table_name: str):
        """获取带有schema前缀的表"""
        full_table = f"{self.SCHEMA}.{table_name}"
        return self.client.table(full_table)
    
    # ========== 用户操作 ==========
    
    def create_or_update_user(self, user_id: str, email: str, 
                             subscription_tier: str = 'free',
                             metadata: Optional[Dict] = None) -> Dict:
        """创建或更新用户"""
        data = {
            'user_id': user_id,
            'auth_user_id': user_id,  # 使用相同的UUID
            'email': email,
            'app_id': self.APP_ID,
            'subscription_tier': subscription_tier,
            'metadata': json.dumps(metadata or {}),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            # 尝试插入/更新
            result = self._get_table('users').upsert(
                data, 
                on_conflict='auth_user_id,app_id'
            ).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            print(f"User upsert error: {e}")
            return data
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        try:
            result = self._get_table('users')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('app_id', self.APP_ID)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Get user error: {e}")
            return None
    
    def update_subscription(self, user_id: str, tier: str, 
                           stripe_customer_id: Optional[str] = None) -> bool:
        """更新用户订阅"""
        try:
            data = {
                'subscription_tier': tier,
                'updated_at': datetime.now().isoformat()
            }
            if stripe_customer_id:
                data['stripe_customer_id'] = stripe_customer_id
            
            result = self._get_table('users')\
                .update(data)\
                .eq('user_id', user_id)\
                .eq('app_id', self.APP_ID)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Update subscription error: {e}")
            return False
    
    # ========== 报告操作 ==========
    
    def save_report(self, user_id: str, birth_info: Dict, 
                   bazi_data: Dict, report_content: Dict,
                   report_id: Optional[str] = None,
                   payment_tier: str = 'monthly') -> Dict:
        """保存报告"""
        data = {
            'report_id': report_id or self._generate_report_id(),
            'user_id': user_id,
            'birth_info': json.dumps(birth_info, ensure_ascii=False),
            'bazi_data': json.dumps(bazi_data, ensure_ascii=False),
            'report_content': json.dumps(report_content, ensure_ascii=False),
            'payment_tier': payment_tier,
            'created_at': datetime.now().isoformat()
        }
        
        try:
            result = self._get_table('reports').insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            print(f"Save report error: {e}")
            return data
    
    def get_reports(self, user_id: str, limit: int = 10) -> List[Dict]:
        """获取用户所有报告"""
        try:
            result = self._get_table('reports')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Get reports error: {e}")
            return []
    
    def get_report(self, report_id: str) -> Optional[Dict]:
        """获取单个报告"""
        try:
            result = self._get_table('reports')\
                .select('*')\
                .eq('report_id', report_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Get report error: {e}")
            return None
    
    def delete_report(self, report_id: str, user_id: str) -> bool:
        """删除报告（验证用户所有权）"""
        try:
            result = self._get_table('reports')\
                .delete()\
                .eq('report_id', report_id)\
                .eq('user_id', user_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Delete report error: {e}")
            return False
    
    # ========== 支付记录 ==========
    
    def save_payment(self, user_id: str, payment_id: str,
                    stripe_session_id: str, amount: int,
                    tier: str, status: str = 'pending') -> Dict:
        """保存支付记录"""
        data = {
            'user_id': user_id,
            'payment_id': payment_id,
            'stripe_session_id': stripe_session_id,
            'amount': amount,
            'currency': 'CNY',
            'tier': tier,
            'status': status,
            'created_at': datetime.now().isoformat()
        }
        
        try:
            result = self._get_table('payments').insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            print(f"Save payment error: {e}")
            return data
    
    def update_payment_status(self, payment_id: str, status: str) -> bool:
        """更新支付状态"""
        try:
            data = {
                'status': status,
                'completed_at': datetime.now().isoformat() if status == 'success' else None
            }
            result = self._get_table('payments')\
                .update(data)\
                .eq('payment_id', payment_id)\
                .execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Update payment error: {e}")
            return False
    
    # ========== 访问日志 ==========
    
    def log_action(self, user_id: str, action: str, 
                  metadata: Optional[Dict] = None) -> bool:
        """记录用户操作"""
        try:
            data = {
                'user_id': user_id,
                'action': action,
                'metadata': json.dumps(metadata or {}),
                'created_at': datetime.now().isoformat()
            }
            result = self._get_table('access_logs').insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Log action error: {e}")
            return False
    
    # ========== 工具方法 ==========
    
    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import uuid
        return f"sf_{uuid.uuid4().hex[:12]}"
    
    def has_active_subscription(self, user_id: str) -> bool:
        """检查用户是否有有效订阅"""
        user = self.get_user(user_id)
        if not user:
            return False
        return user.get('subscription_tier') in ['monthly', 'quarterly', 'annual']


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # 使用 Service Role Key 绕过RLS
    client = SupabaseClient(
        url=os.getenv('SUPABASE_STOCK_URL'),
        key=os.getenv('SUPABASE_SERVICE_ROLE_KEY'),  # 使用 service_role key
        use_service_role=True
    )
    
    # 测试：创建用户
    result = client.create_or_update_user(
        user_id='test_user_123',
        email='test@example.com',
        subscription_tier='monthly'
    )
    print("User:", result)
    
    # 测试：保存报告
    report = client.save_report(
        user_id='test_user_123',
        birth_info={'name': '测试'},
        bazi_data={'bazi': '测试数据'},
        report_content={'page1': {'content': '测试内容'}}
    )
    print("Report:", report)
