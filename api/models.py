import uuid
import shortuuid
from django.utils import timezone
from datetime import timedelta
from django.contrib.gis.db import models
from model_utils import Choices
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models import Q
from api.utils.generate import generate_group_code

# from background_task import background
from .managers import CustomUserManager

import api.utils.gets as g


class Profile(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = Choices(
        ("M", "Male"),
        ("W", "Female"),
        ("X", "Non-binary"),
    )

    SHOW_ME_CHOICES = Choices(
        ("M", "Men"),
        ("W", "Women"),
        ("X", "Everyone"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200, null=True)
    password = models.CharField(max_length=200)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    has_account = models.BooleanField(default=False)
    is_in_group = models.BooleanField(default=False)

    location = models.PointField(srid=4326, blank=True, null=True)

    birthdate = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True)
    nationality = models.TextField(max_length=20, null=True)
    city = models.TextField(max_length=15, null=True)
    university = models.TextField(max_length=40, null=True)
    description = models.TextField(max_length=500, null=True)

    instagram = models.TextField(max_length=15, null=True)

    gender = models.CharField(
        choices=GENDER_CHOICES,
        default=GENDER_CHOICES.M,
        max_length=1,
        null=False,
        blank=False,
    )
    show_me = models.CharField(
        choices=SHOW_ME_CHOICES,
        default=SHOW_ME_CHOICES.W,
        max_length=1,
        null=False,
        blank=False,
    )

    blocked_profiles = models.ManyToManyField(
        "self", symmetrical=False, related_name="blocked_by", blank=True
    )

    # many to many of people that like the current profile
    likes = models.ManyToManyField(
        "self", symmetrical=False, related_name="liked_by", blank=True
    )

    USERNAME_FIELD = "email"
    # requred for creating user
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    # profile methods

    def block_profile(self, blocked_profile):
        # Remove likes between
        self.likes.remove(blocked_profile)
        blocked_profile.likes.remove(self)

        # Check for existing match between profiles and delete it
        match_qs = Match.objects.filter(
            Q(profile1=self, profile2=blocked_profile)
            | Q(profile1=blocked_profile, profile2=self)
        )
        if match_qs.exists():
            match_qs.delete()

        # check is there is any conversation between and delete it
        conversation = g.get_conversation_between(self, blocked_profile)
        if conversation:
            conversation.delete()

        #  check if the user is in a group with the block profile
        group = g.get_group_between(self, blocked_profile)

        if group:
            if group.owner == self:
                group.members.remove(blocked_profile)
            else:
                group.members.remove(self)
            group.save()

        self.blocked_profiles.add(blocked_profile)

    def delete(self):
        conversations = Conversation.objects.filter(participants=self)

        if conversations.count() >= 1:
            for conv in conversations:
                conv.delete()

        super().delete()


class Photo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, default=None, on_delete=models.CASCADE)
    image = models.ImageField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def delete(self):
        self.image.delete(save=False)
        super().delete()


class VerificationCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(
        Profile, related_name="verification_code", on_delete=models.CASCADE
    )
    email = models.EmailField(null=False, blank=False)
    code = models.CharField(max_length=6)
    expiration = models.DateTimeField(default=timezone.now)  # 使用可调用函数

    def __str__(self):
        return self.expiration


class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile1 = models.ForeignKey(
        Profile, related_name="profile1_matches", default=None, on_delete=models.CASCADE
    )
    profile2 = models.ForeignKey(
        Profile, related_name="profile2_matches", default=None, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(default=timezone.now)

    # @background(schedule=60*60-24)
    # def delete_old_matches(self):
    #     """
    #     Delete matches older than 14 days
    #     """
    #     NUMBER_OF_DAYS = 14

    #     try:
    #         old_matches = Match.object.all().filter(
    #             created__gte=datetime.now()-60*60*24*NUMBER_OF_DAYS
    #         )
    #         old_matches.delete()
    #         print(f"Deleted {len(old_matches)} old matches")
    #     except Exception as e:
    #         print(f"Error deleting old matches: {e}")


class Group(models.Model):
    GENDER_CHOICES = Choices(
        ("M", "Male"),
        ("W", "Female"),
        ("X", "Non-binary"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        Profile, default=None, on_delete=models.CASCADE, related_name="owner_profile"
    )
    gender = models.CharField(
        choices=GENDER_CHOICES,
        default=GENDER_CHOICES.M,
        max_length=1,
        null=False,
        blank=False,
    )
    age = models.PositiveIntegerField(null=True)
    total_members = models.PositiveIntegerField(null=True)
    share_link = models.CharField(max_length=100, unique=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    members = models.ManyToManyField(Profile, blank=True, related_name="member_group")

    matches = models.ManyToManyField(Match, blank=True, related_name="matches")
    likes = models.ManyToManyField(Profile, blank=True, related_name="group_likes")

    def save(self, *args, **kwargs):
        # set the link when the group is created
        if not self.share_link:
            self.share_link = f"join.my.group/{generate_group_code()}"

        # get the age of the group
        if not self.age:
            self.age = self.owner.age

        # get the gender of the group
        self.gender = self.owner.gender

        # count the members
        self.total_members = self.members.count()

        super().save(*args, **kwargs)


class MyGroupMessage(models.Model):
    """
    The group itself works as a chat_room and this model as its message
    The group does not require another separate model for the conversation, since our
    application only allows users to be in one group at a time
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, default=None, on_delete=models.CASCADE)
    sender = models.ForeignKey(Profile, default=None, on_delete=models.CASCADE)
    message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)

    def get_sent_time(self):
        return self.sent_at.strftime("%I:%M %p")


class Conversation(models.Model):
    """
    This model acts as the chat_room between the users belonging to a match
    The model is separated from the match
    For now the application only supports conversations type 1-1 (private)
    """

    TYPES = Choices(
        ("PRIVATE", "private"),
        ("GROUP", "group"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(Profile, related_name="conversations")
    created_at = models.DateTimeField(default=timezone.now)
    type = models.CharField(
        choices=TYPES,
        default=TYPES.PRIVATE,
        max_length=10,
        null=True,
        blank=True,
    )

    def delete(self):
        # delete match and remove like relationship
        participants = self.participants.all()
        match = g.get_match(participants[0], participants[1])
        if match:
            match.delete()

        super().delete()


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, default=None, on_delete=models.CASCADE
    )
    sender = models.ForeignKey(Profile, default=None, on_delete=models.CASCADE)
    message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)

    def get_sent_time(self):
        return self.sent_at.strftime("%I:%M %p")

from django.db import models

class UmIndustryLabelLevel1(models.Model):
    id = models.AutoField(primary_key=True)  # 主键
    name = models.CharField(max_length=255)  # 标签名称
    index = models.CharField(max_length=255)  # 标签序号

    class Meta:
        db_table = 'um_industry_label_level1'
        verbose_name = '行业标签一级'
        verbose_name_plural = '行业标签一级'

    def __str__(self):
        return self.name

class UmIndustryLabelLevel2(models.Model):
    id = models.AutoField(primary_key=True)  # 主键
    name = models.CharField(max_length=255)  # 标签名称
    index = models.CharField(max_length=255)  # 标签序号

    class Meta:
        db_table = 'um_industry_label_level2'
        verbose_name = '行业标签二级'
        verbose_name_plural = '行业标签二级'

    def __str__(self):
        return self.name

class UmIndustryLabelLevel3(models.Model):
    id = models.AutoField(primary_key=True)  # 主键
    name = models.CharField(max_length=255)  # 标签名称
    index = models.CharField(max_length=255)  # 标签序号

    class Meta:
        db_table = 'um_industry_label_level3'
        verbose_name = '行业标签三级'
        verbose_name_plural = '行业标签三级'

    def __str__(self):
        return self.name

class UmRegion(models.Model):
    id = models.AutoField(primary_key=True)  # 自动递增的主键字段
    name = models.CharField(max_length=100)  # 字符串字段，最大长度为100

    class Meta:
        db_table = 'um_region'
        verbose_name = '地理区域一级'
        verbose_name_plural = '地理区域一级'

    def __str__(self):
        return self.name  # 返回实际一级地理区域的名称

class UmSubregion(models.Model):
    id = models.AutoField(primary_key=True)  # 自动递增的主键字段
    name = models.CharField(max_length=100)  # 字符串字段，最大长度为100
    region = models.ForeignKey(
        UmRegion,
        on_delete=models.CASCADE,
        related_name='subregion_region'
    )  # 外键关联到UmRegion模型

    class Meta:
        db_table = 'um_subregion'
        verbose_name = '地理区域二级'
        verbose_name_plural = '地理区域二级'

    def __str__(self):
        return f'{self.name} - {self.region.name}'  # 返回包含二级地理区域名称和对应的一级地理区域名称的字符串

class UmCountry(models.Model):
    id = models.AutoField(primary_key=True)  # 自动递增的主键字段
    name = models.CharField(max_length=100)  # 字符串字段，最大长度为100
    numeric_code = models.IntegerField()  # 整数字段，用于存储国家数字代码
    phonecode = models.CharField(max_length=255)  # 字符串字段，最大长度为255，用于存储电话代码
    region_act = models.CharField(max_length=100)  # **注意**：请确认是否需要此字段
    region = models.ForeignKey(
        UmRegion,
        on_delete=models.CASCADE,
        related_name='country_region'
    )  # 外键关联到UmRegion模型
    subregion_act = models.CharField(max_length=255)  # **注意**：请确认是否需要此字段
    subregion = models.ForeignKey(
        UmSubregion,
        on_delete=models.CASCADE,
        related_name='country_subregion'
    )  # 外键关联到UmSubregion模型

    class Meta:
        db_table = 'um_country'
        verbose_name = '地理区域三级'
        verbose_name_plural = '地理区域三级'

    def __str__(self):
        return f'{self.name} - {self.region.name}'

class UmState(models.Model):
    id = models.AutoField(primary_key=True)  # 自动递增的主键字段
    name = models.CharField(max_length=255)  # 字符串字段，最大长度为255
    country = models.ForeignKey(
        UmCountry,
        on_delete=models.CASCADE,
        related_name='state_country'
    )  # 外键关联到UmCountry模型
    country_code = models.CharField(max_length=255)  # 字符串字段，最大长度为255，用于存储国家代码

    class Meta:
        db_table = 'um_state'
        verbose_name = '地理区域四级'
        verbose_name_plural = '地理区域四级'

    def __str__(self):
        return self.name

class UmLanguage(models.Model):
    language_id = models.AutoField(primary_key=True)  # 自动递增的主键字段
    language_name = models.CharField(max_length=255)  # 字符串字段，最大长度为255
    iso_639_1 = models.CharField(max_length=255)  # 字符串字段，最大长度为255，用于存储语言的ISO 639-1代码

    class Meta:
        db_table = 'um_language'
        verbose_name = '沟通语言'
        verbose_name_plural = '沟通语言'
        indexes = [
            models.Index(fields=['language_id'], name='language_id_idx'),  # 定义索引
        ]

    def __str__(self):
        return self.language_name

class UmUserInformation(models.Model):
    # 用户职位选择项
    POSITION_CHOICES = [
        ('经理', '经理'),
        ('主管', '主管'),
        ('工程师', '工程师'),
        ('销售', '销售'),
        ('市场专员', '市场专员'),
        ('人事', '人事'),
        ('财务', '财务'),
    ]

    # 部门选择项
    DEPARTMENT_CHOICES = [
        ('研发部', '研发部'),
        ('销售部', '销售部'),
        ('市场部', '市场部'),
        ('人事部', '人事部'),
        ('财务部', '财务部'),
        ('客服部', '客服部'),
        ('行政部', '行政部'),
        ('生产部', '生产部'),
        ('采购部', '采购部'),
    ]

    # 法规级别选择项
    REGULATION_LEVEL_CHOICES = [
        ('A级', 'A级'),
        ('B级', 'B级'),
        ('C级', 'C级'),
        ('D级', 'D级'),
    ]

    # 用户身份和公司信息
    user_id = models.AutoField(primary_key=True)  # 主键，自增长
    user_avatar = models.BinaryField(blank=True, null=True)  # 用户头像（使用 BinaryField 存储二进制数据）
    user_name = models.CharField(max_length=64)  # 用户姓名
    user_email = models.EmailField(max_length=64, unique=True)  # 用户邮箱，唯一约束
    # 用户邮箱对应的密码
    user_password = models.CharField(max_length=30, null=True)

    user_phone = models.CharField(max_length=30, blank=True, null=True)  # 用户电话
    position = models.CharField(max_length=255, choices=POSITION_CHOICES, blank=True, null=True)  # 职位
    department = models.CharField(max_length=255, choices=DEPARTMENT_CHOICES, blank=True, null=True)  # 部门
    cultural_customs = models.CharField(max_length=255, blank=True, null=True)  # 文化习俗
    regulation_level = models.CharField(max_length=255, choices=REGULATION_LEVEL_CHOICES, blank=True, null=True)  # 法规级别
    certificate = models.BinaryField(blank=True, null=True)  # 证书（使用 BinaryField 存储二进制数据）
    company_name = models.CharField(max_length=64, blank=True, null=True)  # 公司名称
    country = models.ForeignKey(
        'UmCountry',
        on_delete=models.CASCADE,
        related_name='user_informations',
        blank=True,
        null=True
    )  # 外键关联国家
    postal_code = models.CharField(max_length=30, blank=True, null=True)  # 邮政编码
    address_detail = models.CharField(max_length=255, blank=True, null=True)  # 地址详情
    employee_count = models.CharField(max_length=100, blank=True, null=True)  # 员工数量
    annual_revenue = models.CharField(max_length=100, blank=True, null=True)  # 年收入
    company_description = models.TextField(blank=True, null=True)  # 公司描述
    company_video_link = models.CharField(max_length=255, blank=True, null=True)  # 公司视频链接
    official_website = models.CharField(max_length=255, blank=True, null=True)  # 官方网站
    social_media_links = models.TextField(blank=True, null=True)  # 社交媒体链接
    product_description = models.TextField(blank=True, null=True)  # 产品描述
    product_information = models.BinaryField(blank=True, null=True)  # 产品信息（使用 BinaryField 存储二进制数据）

    class Meta:
        db_table = 'um_user_information'
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'

    def __str__(self):
        return self.user_name  # 返回用户姓名作为对象的字符串表示

class UmUserAction(models.Model):
    # 用户行为记录模型

    ACTION_CHOICES = [
        ('like', 'Like'),
        ('indifferent', 'Indifferent'),
        ('handshake', 'Handshake'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        'UmUserInformation',
        on_delete=models.CASCADE,
        related_name='user_actions',
        blank=True,
        null=True
    )
    viewed_user = models.ForeignKey(
        'UmUserInformation',
        on_delete=models.CASCADE,
        related_name='viewed_user_actions',
        blank=True,
        null=True
    )
    start_time = models.DateTimeField()  # 开始时间
    end_time = models.DateTimeField()  # 结束时间
    stay_time = models.IntegerField()  # 停留时间，单位为秒
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)  # 用户行为的描述（选择性字段）

    class Meta:
        db_table = 'um_user_action'
        verbose_name = '用户行为'
        verbose_name_plural = '用户行为'

    def __str__(self):
        return f'User {self.user_id} action on {self.start_time}'

class UmUserTrade(models.Model):
    IDENTITY_CHOICES = [
        ('Buyer', '买方'),
        ('Seller', '卖方'),
    ]
    ORDER_SCALE_CHOICES = [
        ('一万以内', '一万以内'),
        ('十万以内', '十万以内'),
        ('一百万以内', '一百万以内'),
        ('一千万以内', '一千万以内'),
        ('一千万以上', '一千万以上'),
    ]
    DELIVERY_CYCLE_CHOICES = [
        ('一周', '一周'),
        ('一个月', '一个月'),
        ('半年', '半年'),
        ('一年', '一年'),
        ('一年以上', '一年以上'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('Telegraphic Transfer', '电汇 T/T'),
        ('Documents against Payment', '托收 D/P'),
        ('Letter of Credit', '信用证 L/C'),
        ('Online payment platform', '在线支付平台'),
    ]
    COOPERATION_METHOD_CHOICES = [
        ('Agency Cooperation', '代理合作'),
        ('Distribution Cooperation', '分销合作'),
        ('Original Equipment Manufacturing', 'OEM（原始设备制造）'),
        ('Original Design Manufacturing', 'ODM（原始设计制造）'),
        ('Joint Venture', '合资企业'),
        ('Contract Manufacturing', '合同制造'),
        ('Cross-Border E-Commerce Cooperation', '跨境电商合作'),
        ('Trade Agency', '贸易代理'),
    ]
    CERTIFICATION_NAME_CHOICES = [
        ('AAA', '企业信用良好'),
        ('AA', '企业信用较好'),
        ('A', '企业信用尚可'),
    ]

    id = models.AutoField(primary_key=True)  # 主键，自增长
    identity = models.CharField(max_length=10, choices=IDENTITY_CHOICES)  # 用户身份（买方/卖方）
    country = models.ForeignKey(
        'UmCountry',
        on_delete=models.CASCADE,
        related_name='user_trades'
    )  # 外键关联国家
    order_scale = models.CharField(max_length=20, choices=ORDER_SCALE_CHOICES, blank=True, null=True)  # 订单规模
    delivery_cycle = models.CharField(max_length=20, choices=DELIVERY_CYCLE_CHOICES, blank=True, null=True)  # 交付周期
    payment_method = models.CharField(max_length=255, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)  # 付款方式 (使用 JSONField 存储数组)
    communication_method = models.JSONField()  # 沟通方式 (使用 JSONField 存储数组)
    cooperation_method = models.CharField(max_length=255, choices=COOPERATION_METHOD_CHOICES, default='', blank=True)  # 合作模式
    certification_name = models.CharField(max_length=5, choices=CERTIFICATION_NAME_CHOICES)  # 认证名称
    certification_image = models.BinaryField(blank=True, null=True)  # 认证图片（使用 BinaryField 存储二进制数据）
    industry_label = models.JSONField(blank=True, null=True)  # 用户行业标签（使用 JSONField 存储 JSON 数据）

    class Meta:
        db_table = 'um_user_trade'
        verbose_name = '用户交易'
        verbose_name_plural = '用户交易'

    def __str__(self):
        return f"用户交易 - {self.identity} - {self.order_scale}"

class UmUserCommunication(models.Model):
    # 假设 cooperation_type 和 cooperation_flexibility 是选择字段
    COOPERATION_TYPE_CHOICES = [
        ('战略合作伙伴', '战略合作伙伴'),
        ('长期供货协议', '长期供货协议'),
        ('短期订单', '短期订单'),
        ('一次性项目', '一次性项目'),
        ('联合开发项目', '联合开发项目'),
        ('区域代理', '区域代理'),
        ('原材料供应', '原材料供应'),
        ('市场推广', '市场推广'),
        # 添加其他选择项
    ]

    COOPERATION_FLEXIBILITY_CHOICES = [
        ('分批到货', '分批到货'),
        ('货到付款', '货到付款'),
        ('预付款', '预付款'),
        ('固定价格', '固定价格'),
        ('提供技术支持', '提供技术支持'),
        ('共同承担风险', '共同承担风险'),
        # 添加其他选择项
    ]
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        'UmUserInformation',
        on_delete=models.CASCADE,
        related_name='communications'
    )  # 外键关联 UmUserInformation
    primary_language = models.ForeignKey(
        'UmLanguage',
        on_delete=models.CASCADE,
        related_name='user_communications',
        null=True,
        blank=True
    )  # 外键关联 UmLanguage
    online_start_time = models.TimeField()  # 在线开始时间
    online_end_time = models.TimeField()  # 在线结束时间
    timezone = models.CharField(max_length=64, null=True, blank=True)  # 时区，允许为空
    cooperation_type = models.CharField(max_length=64, choices=COOPERATION_TYPE_CHOICES, null=True, blank=True)  # 合作类型，选择字段
    cooperation_flexibility = models.CharField(max_length=64, choices=COOPERATION_FLEXIBILITY_CHOICES, null=True, blank=True)  # 合作灵活性，选择字段
    other_languages = models.JSONField(null=True, blank=True)  # 存储其他语言的 JSON 字段
    renowned_partner = models.TextField(null=True, blank=True)  # 著名合作伙伴，允许为空

    class Meta:
        db_table = 'um_user_communication'
        verbose_name = '用户沟通'
        verbose_name_plural = '用户沟通'

    def __str__(self):
        return f'User {self.user_id} Communication'
