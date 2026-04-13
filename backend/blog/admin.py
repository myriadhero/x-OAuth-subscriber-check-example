from django.contrib import admin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'access_tier', 'is_published', 'created_at', 'updated_at')
    list_filter = ('access_tier', 'is_published', 'created_at')
    search_fields = ('title', 'excerpt', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'excerpt', 'body')}),
        ('Access', {'fields': ('access_tier', 'is_published')}),
    )
