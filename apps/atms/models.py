"""
ATM Social Map — GeoDjango Models
==================================
Three core models that power the crowdsourced ATM map:

  ATM              — The physical ATM location stored as a PostGIS Point.
  Tag              — Reusable crowd-sourced labels (e.g. "Has Coins", "24/7").
  ATMStatusReport  — A crowd report linking a user, an ATM, a status, and tags.
"""

from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.text import slugify

User = get_user_model()


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class BankChoices(models.TextChoices):
    BDO        = 'BDO',       'BDO Unibank'
    BPI        = 'BPI',       'Bank of the Philippine Islands'
    METROBANK  = 'MBK',       'Metrobank'
    LANDBANK   = 'LBP',       'LandBank of the Philippines'
    UNIONBANK  = 'UBP',       'UnionBank'
    RCBC       = 'RCBC',      'RCBC'
    SECURITY   = 'SB',        'Security Bank'
    PNB        = 'PNB',       'Philippine National Bank'
    OTHER      = 'OTHER',     'Other'


class StatusChoices(models.TextChoices):
    ONLINE    = 'ONLINE',     'Online / Operational'
    NO_CASH   = 'NO_CASH',    'No Cash'
    OFFLINE   = 'OFFLINE',    'Offline / Out of Service'
    LONG_LINE = 'LONG_LINE',  'Long Queue'


# ---------------------------------------------------------------------------
# ATM
# ---------------------------------------------------------------------------

class ATM(gis_models.Model):
    """
    Represents a physical ATM machine.
    The `location` field is a PostGIS Point (SRID 4326 — WGS84 lon/lat),
    which enables spatial queries such as distance filtering and bounding-box
    intersection directly in PostgreSQL.
    """

    name     = models.CharField(max_length=150, help_text='Descriptive name, e.g. "BDO Katipunan Branch ATM 1"')
    bank     = models.CharField(max_length=10, choices=BankChoices.choices, default=BankChoices.OTHER)
    location = gis_models.PointField(
        srid=4326,
        help_text='GPS point — longitude first, then latitude (GeoJSON convention).'
    )
    address    = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='atms_added',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ATM'
        verbose_name_plural = 'ATMs'

    def __str__(self):
        return f'{self.get_bank_display()} — {self.name}'

    @property
    def latitude(self):
        return self.location.y

    @property
    def longitude(self):
        return self.location.x

    @property
    def latest_status(self):
        """Return the most recent ATMStatusReport for this ATM, or None."""
        return self.status_reports.order_by('-created_at').first()


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class Tag(models.Model):
    """
    Crowd-sourced labels that can be attached to status reports,
    e.g. "Has Coins", "No Receipt Paper", "Accessible", "24/7".
    """

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# ATMStatusReport
# ---------------------------------------------------------------------------

class ATMStatusReport(models.Model):
    """
    A crowd-sourced status update submitted by a logged-in user.
    Each report carries a status code plus optional free-text note and tags.
    The most recent report per ATM is treated as the ATM's current status.
    """

    atm    = models.ForeignKey(ATM, on_delete=models.CASCADE, related_name='status_reports')
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='atm_reports')
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ONLINE)
    note   = models.TextField(blank=True, default='', help_text='Optional note about the ATM condition.')
    tags   = models.ManyToManyField(Tag, blank=True, related_name='reports')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ATM Status Report'
        verbose_name_plural = 'ATM Status Reports'

    def __str__(self):
        return f'[{self.get_status_display()}] {self.atm} by {self.user} @ {self.created_at:%Y-%m-%d %H:%M}'
