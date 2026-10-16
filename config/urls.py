from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views
from app import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index_view, name='index'),
    path('landing/', views.index_view, name='landing'), # ← 'landing'指定でも最初の画面へ飛べるように追加
    path('signup/', views.signup_view, name='signup'),
    path('signup/done/', views.signup_done_view, name='signup_done'),
    path('login/', views.login_view, name='login'),
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path('settings/maintenance/', views.maintenance_settings_view, name='maintenance_settings'),
    path('contact/', views.contact_view, name='contact'),

    # ▼ ログアウト系の2画面 ▼
    path('logout/', views.logout_view, name='logout'),                         # ① ログアウト確認画面
    path('logout/execute/', views.execute_logout_view, name='execute_logout'), # ② ログアウト実行＆完了画面

    # ▼ パスワードリセット系の4画面 ▼
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset_form.html'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    # ▼ メイン機能画面 ▼
    path('timeline/', views.timeline_view, name='timeline'),
    path('map/', views.map_view, name='map'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('api/ai_suggest/', views.ai_suggest_view, name='ai_suggest'),
    path('api/checkin/', views.checkin_view, name='checkin'),
    path('api/edit_post/<int:post_id>/', views.edit_post_view, name='edit_post'),
    path('api/delete_post/<int:post_id>/', views.delete_post_view, name='delete_post'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('api/edit_profile/', views.edit_profile_api, name='edit_profile_api'),
    path('api/follow_list/<str:username>/<str:list_type>/', views.get_follow_list_api, name='get_follow_list_api'),
    path('api/toggle_follow/<str:username>/', views.toggle_follow_api, name='toggle_follow_api'),
    path('ai_chat/', views.ai_chat_view, name='ai_chat'),
]

# ==========================================
# ▼ 追加：開発中（DEBUG=True）のみ、ローカルの画像ファイルへのアクセスを許可する
# ==========================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
