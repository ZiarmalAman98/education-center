from django.contrib import admin
from .models import ContactMessage, News, Service, SiteSetting

admin.site.site_header = 'Education Center MIS'
admin.site.site_title = 'Education Center MIS'
admin.site.index_title = 'مدیریتي کنټرول پینل'

admin.site.register(SiteSetting)
admin.site.register(Service)
admin.site.register(ContactMessage)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'is_featured', 'published_at')
    list_filter = ('is_published', 'is_featured', 'category')
    search_fields = ('title', 'body')
