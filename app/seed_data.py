import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from app.models import Post

# 管理ユーザーまたはダミーユーザーの取得
admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})

OKAYAMA_SEED_POSTS = [
    # --- 県南エリア ---
    {
        'spot_name': '王子が岳 パークセンター周辺（玉野市）',
        'latitude': 34.4578,
        'longitude': 133.9567,
        'mobility': 'car',
        'category': 'scenery',
        'sub_tags': ['駐車場が広い', '夕日が綺麗', '絶景スポット'],
        'content': '瀬戸内海を一望できる絶景！第1駐車場は広々していて初心者でも停めやすいです。夕方の時間帯が特におすすめ。',
        'image_url': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80',
    },
    {
        'spot_name': '倉敷美観地区 倉敷川沿い（倉敷市）',
        'latitude': 34.5960,
        'longitude': 133.7715,
        'mobility': 'walk',
        'category': 'local',
        'sub_tags': ['季節限定スイーツ', '歩道が広い', '駅チカ散歩'],
        'content': '白壁の町並みをのんびり散策。秋限定の和栗パフェを出している古民家カフェが最高でした。車は近くの大型市営駐車場に入れるのが無難です。',
        'image_url': 'https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=800&q=80',
    },
    # --- 県中・総社エリア ---
    {
        'spot_name': '吉備路 備中国分寺周辺（総社市）',
        'latitude': 34.6712,
        'longitude': 133.7845,
        'mobility': 'bicycle',
        'category': 'scenery',
        'sub_tags': ['平坦で走りやすい', 'サイクルラックあり', '秋のコスモス'],
        'content': '五重塔周辺のコスモスがちょうど見頃を迎えています！サイクリングロードは平坦で走りやすく、休憩スポットにバイクラックも完備されています。',
        'image_url': 'https://images.unsplash.com/photo-1541625602330-2277a4c46182?auto=format&fit=crop&w=800&q=80',
    },
    # --- 県北エリア ---
    {
        'spot_name': '蒜山ジャージーランド（真庭市蒜山）',
        'latitude': 35.3125,
        'longitude': 133.6812,
        'mobility': 'car',
        'category': 'local',
        'sub_tags': ['駐車場が広い', '秋限定スイーツ', '広大な高原'],
        'content': '雄大な大山と蒜山三座を望む高原スポット！駐車場が非常に広大で大型車でも余裕で停められます。秋限定の濃厚チーズケーキと搾りたてミルクが絶品でした。',
        'image_url': 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=800&q=80',
    },
    {
        'spot_name': '奥津渓 渓流沿い遊歩道（鏡野町）',
        'latitude': 35.2285,
        'longitude': 133.9152,
        'mobility': 'walk',
        'category': 'scenery',
        'sub_tags': ['紅葉が見頃', '静かな穴場', '自然散策'],
        'content': '渓谷美と紅葉のコントラストが息をのむ美しさです。渓流沿いの遊歩道は整備されていて歩きやすいですが、周辺の道路は一部道幅が狭い箇所があるため運転は慎重に。',
        'image_url': 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80',
    },
    {
        'spot_name': '津山城 鶴山公園周辺（津山市）',
        'latitude': 35.0628,
        'longitude': 134.0051,
        'mobility': 'bicycle',
        'category': 'local',
        'sub_tags': ['歴史散策', '坂道あり', 'サイクルステーション'],
        'content': '立派な石垣が圧巻。城下町エリアは自転車でのポタリングが小回りが利いて一番楽しめます。津山駅前でレンタサイクルも借りられます。',
        'image_url': 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=80',
    },
]

def run():
    for data in OKAYAMA_SEED_POSTS:
        post, created = Post.objects.get_or_create(
            spot_name=data['spot_name'],
            user=admin_user,
            defaults={
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'mobility': data['mobility'],
                'category': data['category'],
                'sub_tags': data['sub_tags'],
                'content': data['content'],
                'image_url': data['image_url'],
            }
        )
        if created:
            print(f"作成完了: {post.spot_name}")
        else:
            print(f"既存データあり: {post.spot_name}")

if __name__ == '__main__':
    run()