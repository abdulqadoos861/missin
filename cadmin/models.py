from django.db import models

from django.db import models
from frontend.models import ContactMessage

class MessageReply(models.Model):
    message = models.ForeignKey(ContactMessage, related_name='replies', on_delete=models.CASCADE)
    reply_text = models.TextField()
    replied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Reply to "{self.message.subject}" on {self.replied_at.strftime("%Y-%m-%d %H:%M")}'
