"""
Stripe支付集成
"""
import stripe
from datetime import datetime, timedelta

class StripeClient:
    """Stripe支付客户端"""
    
    def __init__(self, secret_key, monthly_price_id, quarterly_price_id):
        stripe.api_key = secret_key
        self.monthly_price_id = monthly_price_id
        self.quarterly_price_id = quarterly_price_id
    
    def create_checkout_session(self, user_id, email, tier='monthly'):
        """创建结账会话"""
        price_id = self.monthly_price_id if tier == 'monthly' else self.quarterly_price_id
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://your-app.com/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://your-app.com/cancel',
            customer_email=email,
            metadata={
                'user_id': user_id,
                'tier': tier
            }
        )
        
        return session
    
    def handle_webhook(self, payload, sig_header, webhook_secret):
        """处理Stripe Webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")
        
        # 处理订阅事件
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            return {
                'type': 'subscription_created',
                'user_id': session['metadata']['user_id'],
                'tier': session['metadata']['tier'],
                'session_id': session['id']
            }
        
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            return {
                'type': 'subscription_cancelled',
                'subscription_id': subscription['id']
            }
        
        return {'type': 'unknown'}
