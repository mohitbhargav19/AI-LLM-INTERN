

# Create your models here.
# persona_generator/models.py

from django.db import models

class Persona(models.Model):
    """
    Model to store a generated user persona.
    """
    reddit_username = models.CharField(max_length=255, unique=True, help_text="Reddit username for which the persona was generated.")
    persona_text = models.TextField(help_text="The full generated user persona text.")
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Persona for {self.reddit_username} ({self.generated_at.strftime('%Y-%m-%d')})"

class PersonaCharacteristic(models.Model):
    """
    Model to store individual characteristics of a persona with their citations.
    """
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='characteristics')
    characteristic = models.CharField(max_length=500, help_text="A specific characteristic of the persona.")
    citations = models.TextField(help_text="JSON string of cited Reddit posts/comments (e.g., [{'url': '...', 'snippet': '...'}])")

    def __str__(self):
        return f"{self.characteristic} for {self.persona.reddit_username}"

    class Meta:
        verbose_name_plural = "Persona Characteristics"