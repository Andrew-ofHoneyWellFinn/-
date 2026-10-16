from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('spot_name', 'user', 'mobility', 'category', 'created_at', 'expires_at')
    list_filter = ('mobility', 'category', 'created_at')
    search_fields = ('spot_name', 'content', 'user__username')