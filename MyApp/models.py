from django.db import models
from django.conf import settings


class LostAndFoundItem(models.Model):
    item_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lost_reports',
        null=True,
        blank=True,
    )
    item_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    date_lost_found = models.DateField()
    image = models.ImageField(
        upload_to='lost_item_images/',
        blank=True,
        null=True,
    )

    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Resolved', 'Resolved'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='Open',
    )

    def __str__(self):
        return self.item_name


class Comment(models.Model):
    item = models.ForeignKey(
        LostAndFoundItem,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lost_item_comments',
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Comment by {} on {}'.format(self.user, self.item)