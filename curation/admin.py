from django.contrib import admin, messages
from .models import Article, Category # Or combine imports


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} # Auto-populate slug from name


@admin.action(description="Fetch content, summarize, and translate selected articles")
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
            f"Successfully processed {success_count} article(s) (fetch, summarize, translate).", 
            messages.SUCCESS
        )
    
    if errors:
        error_message = "Errors encountered:\n" + "\n".join(errors)
        modeladmin.message_user(request, error_message, messages.WARNING)




@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('url', 'title', 'display_categories', 'summary_preview', 'summary_ko_preview', 'reading_time_minutes', 'updated_at', 'created_at')
    list_filter = ('categories', 'created_at', 'updated_at')
    search_fields = ('url', 'title', 'summary', 'summary_ko', 'categories__name')
    readonly_fields = ('created_at', 'updated_at', 'summary', 'summary_ko', 'reading_time_minutes')
    actions = [summarize_selected_articles]
    filter_horizontal = ('categories',)
    
    fieldsets = (
        ('Article Information', {
            'fields': ('url', 'title', 'categories')
        }),
        ('Generated Content', {
            'fields': ('summary', 'summary_ko', 'reading_time_minutes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Categories')
    def display_categories(self, obj):
        """Displays categories as a comma-separated string in the list view."""
        if obj.categories.exists():
            return ", ".join([category.name for category in obj.categories.all()])
        return '-' # Or None, or empty string
        
    def get_readonly_fields(self, request, obj=None):
        # Make 'categories' always read-only as it's set by the LLM
        readonly = list(super().get_readonly_fields(request, obj))
        if 'categories' not in readonly:
             readonly.append('categories')
        return readonly
    
    @admin.display(description='Summary Preview')
    def summary_preview(self, obj):
        if obj.summary:
            preview = obj.summary[:100]
            return f"{preview}..." if len(obj.summary) > 100 else preview
        return "No summary available"
        
    @admin.display(description='Korean Summary Preview')
    def summary_ko_preview(self, obj):
         if obj.summary_ko:
            if obj.summary_ko.startswith("Translation Error"): return obj.summary_ko
            preview = obj.summary_ko[:50]
            return f"{preview}..." if len(obj.summary_ko) > 50 else preview
         return "No Korean summary"
