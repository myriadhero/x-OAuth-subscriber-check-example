from django.contrib import admin
from .models import CreatorXCredential, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'x_user_id',
        'is_x_subscriber',
        'x_subscription_last_checked',
    )
    search_fields = ('user__username', 'user__email', 'x_user_id')
    list_filter = ('is_x_subscriber',)
    readonly_fields = ('x_subscription_last_checked',)


@admin.register(CreatorXCredential)
class CreatorXCredentialAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    fields = ('name', 'bearer_token', 'is_active')

    def has_add_permission(self, request):
        if CreatorXCredential.objects.exists():
            return False
        return super().has_add_permission(request)
