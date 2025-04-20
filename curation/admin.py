from django.contrib import admin, messages
from .models import Article


@admin.action(description="Fetch content and summarize selected articles")
def summarize_selected_articles(modeladmin, request, queryset):
    success_count = 0
    errors = []
    
    for article in queryset:
        result = article.fetch_and_summarize()
        if result.startswith("Error"):
            errors.append(f"{article.url}: {result}")
        else:
            success_count += 1
    
    if success_count > 0:
        modeladmin.message_user(
            request, 
            f"Successfully summarized {success_count} article(s).", 
            messages.SUCCESS
        )
    
    if errors:
        error_message = "Errors encountered:\n" + "\n".join(errors)
        modeladmin.message_user(request, error_message, messages.WARNING)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('url', 'title', 'summary_preview', 'updated_at', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('url', 'title', 'summary')
    readonly_fields = ('created_at', 'updated_at', 'summary')
    actions = [summarize_selected_articles]
    
    fieldsets = (
        ('Article Information', {
            'fields': ('url', 'title')
        }),
        ('Generated Summary', {
            'fields': ('summary',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Summary Preview')
    def summary_preview(self, obj):
        if obj.summary:
            preview = obj.summary[:100]
            return f"{preview}..." if len(obj.summary) > 100 else preview
        return "No summary available"
