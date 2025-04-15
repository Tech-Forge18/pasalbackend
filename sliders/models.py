from django.db import models

class Slider(models.Model):
    image = models.ImageField(upload_to='sliders/')  # Only field: the slider image

    def __str__(self):
        return f"Slider Image {self.id}"  # Simple string representation

    class Meta:
        verbose_name = "Slider"
        verbose_name_plural = "Sliders"