from django.db import models


class StatusChoices(models.TextChoices):
    STATUS_ONE = "STATUS_ONE", "Status One"
    STATUS_TWO = "STATUS_TWO", "Status Two"
    STATUS_THREE = "STATUS_THREE", "Status Three"
    STATUS_FOUR = "STATUS_FOUR", "Status Four"
    STATUS_FIVE = "STATUS_FIVE", "Status Five"


class PlainModel(models.Model):
    boolean_field = models.BooleanField()
    int_field = models.IntegerField(db_index=True)
    char_field = models.CharField(max_length=255)
    choice_field = models.CharField(max_length=16, choices=StatusChoices.choices)
    datetime_field_start = models.DateField()
    datetime_field_stop = models.DateField()


class IndexedModel(models.Model):
    boolean_field = models.BooleanField(db_index=True)
    int_field = models.IntegerField(db_index=True)
    char_field = models.CharField(max_length=255, db_index=True)
    choice_field = models.CharField(
        max_length=16, choices=StatusChoices.choices, db_index=True
    )
    datetime_field_start = models.DateField(db_index=True)
    datetime_field_stop = models.DateField(db_index=True)


class OptimizedModel(models.Model):
    boolean_field = models.BooleanField()
    int_field = models.IntegerField(db_index=True)
    char_field = models.CharField(max_length=255, db_index=True)
    choice_field = models.CharField(max_length=16, choices=StatusChoices.choices)
    datetime_field_start = models.DateField(db_index=True)
    datetime_field_stop = models.DateField(db_index=True)
