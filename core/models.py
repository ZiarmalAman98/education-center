from django.db import models


class SiteSetting(models.Model):
    center_name = models.CharField(max_length=150, default='Education Center')
    slogan = models.CharField(max_length=255, blank=True)
    welcome_title = models.CharField(max_length=255, default='ستاسو د بريا زده‌کړيز مرکز')
    welcome_text = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    facebook_url = models.URLField(blank=True)

    class Meta:
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return self.center_name


class Service(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField()
    icon = models.CharField(max_length=40, default='📚')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class News(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    image_url = models.URLField(blank=True)
    category = models.CharField(max_length=80, default='Announcement')
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name_plural = 'News'

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}: {self.message[:40]}'
