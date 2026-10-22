from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver


# =========================================================
# 1. お出かけ投稿（親テーブル）
# =========================================================
class Post(models.Model):
    # 移動手段の選択肢
    MOBILITY_CHOICES = (
        ('car', '🚗 車'),
        ('bicycle', '🚲 自転車'),
        ('walk', '🚶 徒歩'),
    )
    # 3大リアルタイム情報のカテゴリ
    CATEGORY_CHOICES = (
        ('scenery', '🍁 景観・季節もの'),
        ('road', '🛣️ 道路・混雑状況'),
        ('local', '📍 地域のみどころ'),
    )
    # ★ 追加：エリアの選択肢（後から増やせます）
    AREA_CHOICES = (
        ('okayama_city', '🏙️ 岡山・駅前エリア'),
        ('kurashiki', '🏘️ 倉敷・美観地区エリア'),
        ('kibiji', '🚲 吉備路エリア'),
        ('setouchi', '🌊 瀬戸内・玉野エリア'),
        ('northern', '🏔️ 備北・県北エリア'),
        ('other', '📍 その他エリア'),
    )

    # 投稿者情報
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name='投稿者')
    spot_name = models.CharField(max_length=100, verbose_name='スポット名・場所')
    
    # ★ 追加：エリアとテナント情報
    area = models.CharField(max_length=20, choices=AREA_CHOICES, default='other', verbose_name='エリア')
    tenant = models.CharField(max_length=100, blank=True, null=True, verbose_name='テナント・施設名')

    # 位置情報（岡山県全域の座標）
    latitude = models.FloatField(verbose_name='緯度', default=34.6655)
    longitude = models.FloatField(verbose_name='経度', default=133.9180)
    
    # 移動手段＆情報カテゴリ
    mobility = models.CharField(max_length=10, choices=MOBILITY_CHOICES, default='car', verbose_name='移動手段')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='local', verbose_name='カテゴリ')
    
    # 構造化タグ（「駐車場が広い」「季節もの」などをリストで保存）
    sub_tags = models.JSONField(default=list, blank=True, verbose_name='タグ一覧')
    
    # 投稿本文
    content = models.TextField(verbose_name='感想・状況コメント')

    # 時間管理（作成日時とデータの賞味期限）
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='投稿日時')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='データ有効期限')

    # リアクション
    likes_count = models.PositiveIntegerField(default=0, verbose_name='いいね数')
    wants_count = models.PositiveIntegerField(default=0, verbose_name='行ってみたい数')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'お出かけ投稿'
        verbose_name_plural = 'お出かけ投稿一覧'

    def __str__(self):
        return f"[{self.get_mobility_display()}] {self.spot_name} (@{self.user.username})"

    # カテゴリに応じた有効期限（TTL）を保存時に自動設定するロジック
    def save(self, *args, **kwargs):
        if not self.expires_at:
            if self.category == 'road':
                # 混雑などの道路状況：3時間
                self.expires_at = timezone.now() + timedelta(hours=3)
            elif self.category == 'scenery':
                # 桜や紅葉などの景観：14日間
                self.expires_at = timezone.now() + timedelta(days=14)
            else:
                # 地域のみどころ：無期限（NULL）
                self.expires_at = None
        super().save(*args, **kwargs)


# =========================================================
# 2. 投稿画像（子テーブル：1つの投稿に複数枚紐づく）
# =========================================================
class PostImage(models.Model):
    # Postが削除されたら、それに紐づく画像も一緒に削除される（CASCADE設定）
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images', verbose_name='対象の投稿')
    
    # AWS S3対応のImageField
    image = models.ImageField(upload_to='spot_images/', verbose_name='写真')
    
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='アップロード日時')

    class Meta:
        ordering = ['uploaded_at'] # 投稿された順番に並べる
        verbose_name = '投稿写真'
        verbose_name_plural = '投稿写真一覧'

    def __str__(self):
        return f"{self.post.spot_name} の画像"
    
# =========================================================
# 3. 訪問履歴（チェックイン機能用）
# =========================================================
class VisitHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='visit_histories', verbose_name='ユーザー')
    spot_name = models.CharField(max_length=100, verbose_name='スポット名・場所')
    latitude = models.FloatField(verbose_name='緯度', default=34.6655)
    longitude = models.FloatField(verbose_name='経度', default=133.9180)
    visited_at = models.DateTimeField(auto_now_add=True, verbose_name='訪問日時')

    class Meta:
        ordering = ['-visited_at']
        verbose_name = '訪問履歴'
        verbose_name_plural = '訪問履歴一覧'

    def __str__(self):
        return f"{self.spot_name} ({self.user.username})"
    
# ===============================================
# ★ 追加：ユーザーのプロフィール情報を管理するモデル
# ===============================================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 自己紹介文（最大200文字など、任意で設定）
    bio = models.TextField("プロフィール文", max_length=200, blank=True, null=True)
    
    # アイコン画像（設定されない場合はデフォルトアイコンを表示する想定）
    avatar = models.ImageField("アイコン画像", upload_to='avatars/', blank=True, null=True)
    
    # ヘッダー画像（背景画像）
    header_image = models.ImageField("ヘッダー画像", upload_to='headers/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}のプロフィール"

# --- 以下は「ユーザーが新規登録された時に、自動的に空のプロフィール枠を作る」ための魔法のコード ---
@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        try:
            instance.profile.save()
        except getattr(User, 'profile').RelatedObjectDoesNotExist:
            Profile.objects.create(user=instance)
    
# ===============================================
# ★ 追加：フォロー関係を管理するモデル
# ===============================================
class Follow(models.Model):
    # フォローする人（自分）
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    # フォローされる人（相手）
    following = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class SiteSetting(models.Model):
    maintenance_mode = models.BooleanField(default=False, verbose_name='メンテナンス中')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        verbose_name = 'サイト設定'
        verbose_name_plural = 'サイト設定'

    def __str__(self):
        return 'サイト設定'
    
# ===============================================
# ★ 追加：コメントを管理するモデル
# ===============================================
class Comment(models.Model):
    # どの投稿へのコメントか
    post = models.ForeignKey(Post, related_name='post_comments', on_delete=models.CASCADE, verbose_name='対象の投稿')
    # 誰がコメントしたか
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='コメントしたユーザー')
    # コメント内容
    text = models.TextField("コメント内容", max_length=500)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='コメント日時')

    class Meta:
        ordering = ['created_at'] # 古い順（チャットアプリのような順番）に並べる
        verbose_name = 'コメント'
        verbose_name_plural = 'コメント一覧'

    def __str__(self):
        return f"{self.user.username} - {self.post.spot_name}へのコメント"
    
# ===============================================
# ★ 追加：いいねとブックマークを管理するモデル
# ===============================================
class Like(models.Model):
    post = models.ForeignKey(Post, related_name='post_likes', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user') # 1人1回まで

    def __str__(self):
        return f"{self.user.username} likes {self.post.spot_name}"

class Bookmark(models.Model):
    post = models.ForeignKey(Post, related_name='post_bookmarks', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user') # 1人1回まで

    def __str__(self):
        return f"{self.user.username} bookmarked {self.post.spot_name}"
    
# ==========================================
# ★ 追加：DM（ダイレクトメッセージ）モデル
# ==========================================
class DirectMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='送信者')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name='受信者')
    message = models.TextField(verbose_name='メッセージ')
    is_read = models.BooleanField(default=False, verbose_name='既読フラグ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='送信日時')

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.message[:20]}"