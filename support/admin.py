from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'text', 'author', 'created_at')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'language', 'operator', 'last_message_at')
    list_filter = ('status', 'language')
    search_fields = ('visitor_name', 'visitor_phone', 'messages__text')
    inlines = [MessageInline]
