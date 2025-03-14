from console.models.main import SMSVerificationCode
from django.utils import timezone

class SMSVerificationCodeRepository(object):
    def create_verification(self, phone, code, purpose, expires_at):
        return SMSVerificationCode.objects.create(
            phone=phone,
            code=code, 
            purpose=purpose,
            expires_at=expires_at
        )

    def get_recent_code(self, phone, minutes=1):
        """获取最近一分钟内的验证码"""
        time_threshold = timezone.now() - timezone.timedelta(minutes=minutes)
        return SMSVerificationCode.objects.filter(
            phone=phone,
            created_at__gt=time_threshold
        ).first()
    
    def count_today_codes(self, phone):
        """获取今天发送的验证码数量"""
        today = timezone.now().replace(hour=0, minute=0, second=0)
        return SMSVerificationCode.objects.filter(
            phone=phone,
            created_at__gt=today
        ).count()

    def get_valid_code(self, phone, purpose):
        """获取有效的验证码"""
        return SMSVerificationCode.objects.filter(
            phone=phone,
            purpose=purpose,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()

sms_repo = SMSVerificationCodeRepository() 