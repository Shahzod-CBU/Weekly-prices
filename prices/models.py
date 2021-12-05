from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from datetime import timedelta


GROUP_CHOICES = (
    ('Food', 'Озиқ-овқат'),
    ('Non-food', 'Ноозиқ-овқат'),
    ('Service', 'Хизмат')
)


class Good(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    weight = models.FloatField(max_length=255, validators=[MinValueValidator(0), MaxValueValidator(1)])
    description = models.CharField(max_length=255, null=True, blank=True)
    group = models.CharField(max_length=255, choices=GROUP_CHOICES)
    visible = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(unique=True, null=True)
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']


class Region(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    population = models.FloatField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


class Market(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default='Бозор')
    market_order =  models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(6)])
    is_market = models.BooleanField(default=True)

    class Meta:
        ordering = ['region_id', 'market_order']
        unique_together = ("region", "market_order")

    def __str__(self):
        return self.name


# actually to monday
def to_sunday():
    day = timezone.datetime.today()
    week_day = day.weekday()
    return day + timedelta(days=((7 if week_day else 0)-week_day))


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, blank=True, null=True)
    
    class Meta:
        ordering = ['region']  

    def __str__(self):
        return f'{self.user.first_name[0]}. {self.user.last_name}' if self.user.first_name else ''


class Price(models.Model):
    price = models.PositiveIntegerField(null=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    good = models.ForeignKey(Good, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    sunday = models.DateField(default=to_sunday)
    author = models.ForeignKey(Profile, on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.datetime.now)

    class Meta:
        unique_together = ("region", "good", "market", "sunday")

    def __str__(self):
        return self.good.name


class MarketWeight(models.Model):
    good = models.ForeignKey(Good, on_delete=models.CASCADE)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    weight = models.FloatField(max_length=32)

    class Meta:
        ordering = ['good', 'region']
        unique_together = ('good', 'region')

    def __str__(self):
        return f'{self.good}_{self.region}={self.weight}'


class SetDate(models.Model):
    date = models.DateField(default=to_sunday, null=True, blank=True)
    show_default = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'date'
        verbose_name_plural = 'Set date'

    def __str__(self):
        return self.date.strftime('%Y-%m-%d')


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    
    try:
        instance.profile.save()
    except ObjectDoesNotExist:
        Profile.objects.create(user=instance)