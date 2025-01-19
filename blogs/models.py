# models.py
from django.db import models

class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    language = models.CharField(max_length=20, default='English')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
