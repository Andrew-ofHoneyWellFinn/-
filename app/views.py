import os
import json
import time # APIリトライ待機用
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
from django.utils.timezone import localtime
from django.utils import timezone
from django.db.models import Q 
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings # ★追加：settings.pyからAPIキーを取得するため
from google import genai

from .models import Post, PostImage, SiteSetting, VisitHistory, Profile, Follow
from .forms import ContactForm, SignUpForm


# ▼ プロフィールやトレンドのモックデータ
MOCK_TRENDS = [
    {'rank': 1, 'tag': '#秋限定スイーツ', 'category': '季節もの・グルメ', 'count': '128件の投稿'},
    {'rank': 2, 'tag': '#初心者でも停めやすい駐車場', 'category': '車・安心スポット', 'count': '94件の投稿'},
    {'rank': 3, 'tag': '#夕日が見頃', 'category': 'リアルタイム景観', 'count': '76件の投稿'},
    {'rank': 4, 'tag': '#吉備路サイクリング', 'category': '自転車・ルート', 'count': '53件の投稿'},
    {'rank': 5, 'tag': '#道幅狭め注意', 'category': '道路状況シェア', 'count': '41件の投稿'},
]

def index_view(request):
    if request.user.is_authenticated:
        # ▼ スマホならマップへ、PCならタイムラインへ
        if getattr(request, 'user_agent', None) and request.user_agent.is_mobile:
            return redirect('map')
        return redirect('timeline')
    return render(request, 'index.html')

@never_cache
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('signup_done')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def signup_done_view(request):
    return render(request, 'signup_done.html')

@login_required
def contact_view(request):
    submitted = False
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            send_mail(
                subject=f"[旅ミッケ] {form.cleaned_data['subject']}",
                message=(
                    f"送信者: {request.user.username} ({request.user.email})\n\n"
                    f"{form.cleaned_data['message']}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            submitted = True
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form, 'submitted': submitted})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            site_setting = SiteSetting.objects.order_by('pk').first()
            if site_setting and site_setting.maintenance_mode and not (user.is_staff or user.is_superuser):
                return redirect('maintenance')
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            
            # ▼ スマホならマップへ、PCならタイムラインへ
            if getattr(request, 'user_agent', None) and request.user_agent.is_mobile:
                return redirect('map')
            return redirect('timeline')
    else:
        form = AuthenticationForm()
    
    form.fields['username'].label = 'ユーザー名 または メールアドレス'
    form.fields['password'].label = 'パスワード'
    return render(request, 'login.html', {'form': form})

def maintenance_view(request):
    return render(request, 'maintenance.html')

def is_site_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@user_passes_test(is_site_admin)
def maintenance_settings_view(request):
    site_setting, _ = SiteSetting.objects.get_or_create(pk=1)
    if request.method == 'POST':
        site_setting.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        site_setting.save(update_fields=['maintenance_mode', 'updated_at'])
    return render(request, 'maintenance_settings.html', {'site_setting': site_setting})

def logout_view(request):
    return render(request, 'logout_confirm.html')

def execute_logout_view(request):
    logout(request)
    return render(request, 'logout_complete.html')

def password_reset_view(request):
    return render(request, 'password_reset.html')

# ---------------------------------------------------------
# ⑦ SNS（トレンド・タイムライン）画面
# ---------------------------------------------------------
def timeline_view(request):
    posts = Post.objects.all().order_by('-created_at')
    now = timezone.now()

    # 自分がフォローしているユーザーのIDリストをあらかじめ取得
    following_user_ids = []
    if request.user.is_authenticated:
        following_user_ids = list(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))

    for post in posts:
        post.user_initial = post.user.username[0].upper() if post.user else 'G'
        post.category_label = post.get_category_display()
        post.mobility_label = post.get_mobility_display()
        post.likes = 0
        post.wants = 0
        post.comments = 0

        # この投稿をした人を自分がフォローしているか判定
        post.is_following = False
        if post.user and request.user.is_authenticated:
            post.is_following = post.user.id in following_user_ids

        # タイムラインで1枚目の画像を表示するための準備
        first_image = post.images.first()
        post.first_image_url = first_image.image.url if first_image else ''

        time_diff = now - post.created_at
        post.is_expired = bool(post.expires_at and post.expires_at < now)

        if time_diff.days == 0:
            post.freshness = "🔥 NEW (24時間以内)"
            post.freshness_color = "bg-red-100 text-red-700 border-red-200"
        elif time_diff.days < 7:
            post.freshness = "✨ 新着 (1週間以内)"
            post.freshness_color = "bg-blue-100 text-blue-700 border-blue-200"
        elif time_diff.days > 30:
            post.freshness = "🕰️ 1ヶ月以上経過"
            post.freshness_color = "bg-gray-100 text-gray-500 border-gray-200"
        else:
            post.freshness = "" 

    # 自分が過去に投稿したスポット名の履歴を取得
    spot_history = []
    if request.user.is_authenticated:
        raw_history = VisitHistory.objects.filter(user=request.user).order_by('-visited_at').values_list('spot_name', flat=True)
        spot_history = list(dict.fromkeys(raw_history))

    context = {
        'posts': posts,
        'trends': MOCK_TRENDS,
        'spot_history': spot_history,
    }

    # ★ スマホとPCでHTMLを出し分ける
    if getattr(request, 'user_agent', None) and request.user_agent.is_mobile:
        return render(request, 'mobile/timeline.html', context)
    return render(request, 'timeline.html', context)

# ---------------------------------------------------------
# ⑧ プロフィール画面
# ---------------------------------------------------------
def profile_view(request, username):
    target_user = get_object_or_404(User, username=username)
    profile = getattr(target_user, 'profile', None)
    
    is_following = False
    if request.user.is_authenticated and request.user != target_user:
        is_following = Follow.objects.filter(follower=request.user, following=target_user).exists()
    
    user_posts = Post.objects.filter(user__username=username).order_by('-created_at')
    now = timezone.now()
    
    for post in user_posts:
        post.user_initial = post.user.username[0].upper() if post.user else 'G'
        post.category_label = post.get_category_display()
        post.mobility_label = post.get_mobility_display()
        post.likes = 0
        post.wants = 0
        post.comments = 0
        
        first_image = post.images.first()
        post.first_image_url = first_image.image.url if first_image else ''

        time_diff = now - post.created_at
        post.is_expired = bool(post.expires_at and post.expires_at < now)
        if time_diff.days == 0:
            post.freshness = "🔥 NEW"
            post.freshness_color = "bg-red-100 text-red-700 border-red-200"
        elif time_diff.days > 30:
            post.freshness = "🕰️ 古い情報"
            post.freshness_color = "bg-gray-100 text-gray-500 border-gray-200"
        else:
            post.freshness = ""

    context = {
        'target_user': target_user,
        'profile': profile,
        'posts': user_posts,
        'is_following': is_following,
    }

    # ★ スマホとPCでHTMLを出し分ける
    if getattr(request, 'user_agent', None) and request.user_agent.is_mobile:
        return render(request, 'mobile/profile.html', context)
    return render(request, 'profile.html', context)


# ---------------------------------------------------------
# ⑨ 地図（マップピン）画面 ＆ ピン新規登録処理
# ---------------------------------------------------------
def map_view(request):
    if request.method == 'POST':
        user = request.user if request.user.is_authenticated else None
        if not user:
            return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=403)

        spot_name = request.POST.get('spot_name', '名称未設定')
        area = request.POST.get('area', 'other')
        tenant = request.POST.get('tenant', '')
        category = request.POST.get('category', 'local')
        mobility = request.POST.get('mobility', 'car')
        content = request.POST.get('content', '')
        lat = float(request.POST.get('lat', 34.6655))
        lng = float(request.POST.get('lng', 133.9180))
        sub_tags = request.POST.getlist('sub_tags')
        images = request.FILES.getlist('images')

        new_post = Post.objects.create(
            user=user,
            spot_name=spot_name,
            area=area,
            tenant=tenant,
            latitude=lat,
            longitude=lng,
            mobility=mobility,
            category=category,
            content=content,
            sub_tags=sub_tags,
        )

        for img in images[:4]:
            PostImage.objects.create(post=new_post, image=img)

        first_image = new_post.images.first()
        image_url = first_image.image.url if first_image else ''

        post_data = {
            'id': new_post.id,
            'username': new_post.user.username,
            'spot_name': new_post.spot_name,
            'lat': new_post.latitude,
            'lng': new_post.longitude,
            'category': new_post.category,
            'category_label': new_post.get_category_display(),
            'mobility': new_post.mobility,
            'mobility_label': new_post.get_mobility_display(),
            'sub_tags': new_post.sub_tags,
            'content': new_post.content,
            'image_url': image_url,
            'created_at': localtime(new_post.created_at).strftime('%m月%d日 %H:%M'),
            'created_timestamp': int(new_post.created_at.timestamp() * 1000),
        }
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'spot': post_data})
        else:
            return redirect('timeline')

    # --- GET処理（マップ表示） ---
    now = timezone.now()
    valid_posts = Post.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).order_by('-created_at')

    spots_data = []
    for p in valid_posts:
        first_image = p.images.first()
        spots_data.append({
            'id': p.id,
            'username': p.user.username if p.user else 'ゲスト',
            'spot_name': p.spot_name,
            'lat': p.latitude,
            'lng': p.longitude,
            'category': p.category,
            'category_label': p.get_category_display(),
            'mobility': p.mobility,
            'mobility_label': p.get_mobility_display(),
            'sub_tags': p.sub_tags,
            'content': p.content,
            'image_url': first_image.image.url if first_image else '', 
            'created_at': localtime(p.created_at).strftime('%m月%d日 %H:%M'),
            'created_timestamp': int(p.created_at.timestamp() * 1000), 
        })

    context = {
        # ★settings.pyからAPIキーを取得するように変更
        'api_key': settings.GOOGLE_MAPS_API_KEY,
        'posts': spots_data,
    }

    # ★ スマホとPCでHTMLを出し分ける
    if getattr(request, 'user_agent', None) and request.user_agent.is_mobile:
        return render(request, 'mobile/map.html', context)
    return render(request, 'map.html', context)

# ▼ 誰でもアクセスできるようにする
def ai_chat_view(request):
    return render(request, 'mobile/ai.html')

# ---------------------------------------------------------
# ★ AIお出かけコンシェルジュAPI連携関数 
# ---------------------------------------------------------
def ai_suggest_view(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body)
        mobility = data.get('mobility', '')
        duration = data.get('duration', '')
        companion = data.get('companion', '')
        mood = data.get('mood', '')
        free_text = data.get('free_text', '')

        now = timezone.now()
        valid_posts = Post.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).order_by('-created_at')

        db_info_list = []
        for p in valid_posts:
            db_info_list.append(
                f"- ID: {p.id}, スポット名: {p.spot_name}, 投稿者: {p.user.username if p.user else 'ゲスト'}, "
                f"移動手段: {p.get_mobility_display()}, カテゴリ: {p.get_category_display()}, "
                f"特徴タグ: {', '.join(p.sub_tags)}, 感想内容: {p.content}"
            )
        
        db_context_text = "\n".join(db_info_list)
        if not db_context_text:
            db_context_text = "（現在、登録されているスポット情報はありません）"

        prompt = f"""
        あなたは「旅ミッケ」という地域お出かけアプリの優秀なAIコンシェルジュです。
        以下の【ユーザーの希望条件】と、アプリに登録されている【ユーザー投稿データ】を読み込み、
        ユーザーの条件に最もマッチするスポットを1つ〜2つ選んで、提案の回答文を作成してください。

        【ユーザーの希望条件】
        ・移動手段: {mobility}
        ・所要時間: {duration}
        ・誰と行く: {companion}
        ・今の気分: {mood}
        ・自由入力: {free_text}

        【ユーザー投稿データ（データベースの内容）】
        {db_context_text}

        【回答作成ルール（厳守事項）】
        1. 必ず「ユーザー投稿データ」に記載されている情報のみを根拠にしてください。
        2. 条件に合うものがない場合は、無理に嘘をつかず「条件にピッタリ合う投稿がまだない」旨を伝えてください。
        3. 回答はWebサイト上で直接表示するため、見やすいHTMLタグを使って装飾してください。マークダウンは使用禁止です。
        4. 提案する際は、「なぜおすすめなのか」を具体的に引用して教えてください。
        5. 各スポットの説明のすぐ下に、以下の形式のHTMLボタンを配置してください。
           <button type="button" class="mt-2 mb-6 w-full py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 font-bold text-xs rounded transition flex items-center justify-center gap-1" onclick="jumpToSpotOnMap([lat], [lng], [ID])">
               <span>📍</span> この場所を地図で見る
           </button>
           ※ [lat]、[lng]、[ID] の部分は、選んだスポットの実際の数値に置き換えてください。
        """
        
        # ★ settings.pyからAPIキーを取得
        gemini_api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not gemini_api_key:
            return JsonResponse({'status': 'error', 'message': 'APIキーが設定されていません。'}, status=500)

        client = genai.Client(api_key=gemini_api_key)
        
        # ★ 混雑時のAPIリトライ機能（最大3回）
        max_retries = 3
        ai_html_answer = ""
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash", # 混雑を避けるため1.5-flashを指定
                    contents=prompt
                )
                ai_html_answer = response.text
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Gemini API 混雑のため再試行します (試行 {attempt + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise e

        return JsonResponse({
            'status': 'ok',
            'answer_html': ai_html_answer
        })

    except Exception as e:
        print("Gemini API Error:", str(e))
        return JsonResponse({
            'status': 'error',
            'message': 'AIの呼び出し中にエラーが発生しました。しばらく経ってから再度お試しください。'
        }, status=500)
        
# ==========================================
# ★ チェックイン（訪問履歴の保存）API
# ==========================================
def checkin_view(request):
    if request.method == 'POST':
        user = request.user if request.user.is_authenticated else None
        if not user:
            return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=403)
        
        try:
            data = json.loads(request.body)
            spot_name = data.get('spot_name')
            lat = data.get('lat')
            lng = data.get('lng')

            VisitHistory.objects.create(
                user=user,
                spot_name=spot_name,
                latitude=lat,
                longitude=lng
            )
            return JsonResponse({'status': 'ok', 'message': 'チェックインしました'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

# ==========================================
# ★ 投稿の編集・削除API
# ==========================================
def edit_post_view(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        
        if request.user != post.user:
            return JsonResponse({'status': 'error', 'message': '編集権限がありません'}, status=403)
        
        post.spot_name = request.POST.get('spot_name', post.spot_name)
        post.category = request.POST.get('category', post.category)
        post.mobility = request.POST.get('mobility', post.mobility)
        post.content = request.POST.get('content', post.content)
        post.sub_tags = request.POST.getlist('sub_tags')
        
        images = request.FILES.getlist('images')
        if images:
            post.images.all().delete()
            for img in images[:4]:
                PostImage.objects.create(post=post, image=img)
                
        post.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': '無効なリクエストです'}, status=400)

def delete_post_view(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        
        if request.user != post.user:
            return JsonResponse({'status': 'error', 'message': '削除権限がありません'}, status=403)
            
        post.delete()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error', 'message': '無効なリクエストです'}, status=400)


# ★ プロフィール編集を受け付けるAPI
@login_required
@require_POST
def edit_profile_api(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    
    first_name = request.POST.get('first_name', '').strip()
    bio = request.POST.get('bio', '')
    
    if first_name:
        user.first_name = first_name
        user.save()
        
    profile.bio = bio
    
    if 'avatar' in request.FILES:
        profile.avatar = request.FILES['avatar']
    if 'header_image' in request.FILES:
        profile.header_image = request.FILES['header_image']
        
    profile.save()
    
    return JsonResponse({'status': 'ok', 'message': 'プロフィールを更新しました'})

# ★ フォロー・フォロワー一覧を返すAPI
def get_follow_list_api(request, username, list_type):
    target_user = get_object_or_404(User, username=username)
    users_data = []
    
    if list_type == 'following':
        follows = Follow.objects.filter(follower=target_user).select_related('following__profile')
        for f in follows:
            u = f.following
            users_data.append({
                'username': u.username,
                'name': u.first_name or u.username,
                'avatar_url': u.profile.avatar.url if hasattr(u, 'profile') and u.profile.avatar else None,
                'bio': u.profile.bio if hasattr(u, 'profile') and u.profile.bio else '',
            })
            
    elif list_type == 'followers':
        follows = Follow.objects.filter(following=target_user).select_related('follower__profile')
        for f in follows:
            u = f.follower
            users_data.append({
                'username': u.username,
                'name': u.first_name or u.username,
                'avatar_url': u.profile.avatar.url if hasattr(u, 'profile') and u.profile.avatar else None,
                'bio': u.profile.bio if hasattr(u, 'profile') and u.profile.bio else '',
            })
            
    return JsonResponse({'status': 'ok', 'users': users_data})


@login_required
@require_POST
def toggle_follow_api(request, username):
    target_user = get_object_or_404(User, username=username)
    user = request.user

    if user == target_user:
        return JsonResponse({'status': 'error', 'message': '自分自身はフォローできません'})

    follow_obj = Follow.objects.filter(follower=user, following=target_user).first()

    if follow_obj:
        follow_obj.delete()
        is_following = False
    else:
        Follow.objects.create(follower=user, following=target_user)
        is_following = True

    followers_count = Follow.objects.filter(following=target_user).count()

    return JsonResponse({
        'status': 'ok',
        'is_following': is_following,
        'followers_count': followers_count
    })