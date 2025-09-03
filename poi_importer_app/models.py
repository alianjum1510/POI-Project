from django.db import models

class PoI(models.Model):
    poi_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    ratings = models.JSONField() 
    avg_rating = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.ratings:
            self.avg_rating = sum(self.ratings) / len(self.ratings)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PoI Record: {', '.join(f'{key}: {value}' for key, value in vars(self).items())}"