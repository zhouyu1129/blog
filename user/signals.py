from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_migrate)
def create_default_admin(sender, **kwargs):
    """
    在数据库迁移后检查是否有用户，如果没有则创建默认管理员
    """
    if sender.name == 'user':
        try:
            if not User.objects.exists():
                logger.info("数据库中没有用户，正在创建默认管理员...")
                
                admin_user = User.objects.create_user(
                    username='admin',
                    email='admin@admin.com',
                    password='admin',
                    student_number='0000000000',
                    email_verified=True,
                    is_staff=True,
                    is_superuser=True
                )
                
                logger.info(f"默认管理员创建成功: {admin_user.email}")
                print("\n" + "="*50)
                print("默认管理员账户已创建")
                print("="*50)
                print(f"邮箱: admin@admin.com")
                print(f"密码: admin")
                print("="*50 + "\n")
            else:
                logger.info("数据库中已有用户，跳过创建默认管理员")
        except Exception as e:
            logger.error(f"创建默认管理员失败: {e}")
            print(f"\n警告: 创建默认管理员失败 - {e}\n")