"""
ATM Social Map — GeoDjango Models
==================================
Models mapped from the ATMosphere ERD:
  - Bank: Banks operating ATMs.
  - CardNetwork: Card payment networks (e.g., BancNet, Visa, Mastercard).
  - NetworkAlliance: Alliance between a Bank and a Card Network (fee-free status, surcharge).
  - ATM: Physical ATM machine with latitude and longitude (and PostGIS Point when GIS is active).
  - ATMNetwork: Junction model connecting ATMs to CardNetworks.
  - StatusReport: Crowd-sourced status (online, has_cash).
  - ATMReport: Crowd-sourced discrepancy/issue reports (fee discrepancy, inaccurate location, general notes).
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

try:
    from django.contrib.gis.db import models as gis_models
    from django.contrib.gis.geos import Point
    HAS_GIS = True
except Exception:
    gis_models = models
    Point = None
    HAS_GIS = False


# ---------------------------------------------------------------------------
# 1. Bank
# ---------------------------------------------------------------------------
class Bank(models.Model):
    """Represents a banking institution."""
    bank_id = models.AutoField(primary_key=True)
    bank_name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'banks'
        verbose_name = _('Bank')
        verbose_name_plural = _('Banks')
        ordering = ['bank_name']

    def __str__(self):
        return self.bank_name


# ---------------------------------------------------------------------------
# 2. Card Networks
# ---------------------------------------------------------------------------
class CardNetwork(models.Model):
    """Represents a card network (e.g. BancNet, Visa, Mastercard, JCB)."""
    network_id = models.AutoField(primary_key=True)
    network_name = models.CharField(max_length=150)
    logo_url = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'card_networks'
        verbose_name = _('Card Network')
        verbose_name_plural = _('Card Networks')
        ordering = ['network_name']

    def __str__(self):
        return self.network_name


# ---------------------------------------------------------------------------
# 3. Network Alliances
# ---------------------------------------------------------------------------
class NetworkAlliance(models.Model):
    """Represents an alliance/interchange agreement between a Bank and a Card Network."""
    alliance_id = models.AutoField(primary_key=True)
    card_network = models.ForeignKey(
        CardNetwork,
        on_delete=models.CASCADE,
        related_name='alliances',
        db_column='card_network_id',
    )
    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        related_name='alliances',
        db_column='bank_id',
    )
    is_fee_free = models.BooleanField(default=False)
    surcharge_amt = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'network_alliances'
        verbose_name = _('Network Alliance')
        verbose_name_plural = _('Network Alliances')
        unique_together = ('card_network', 'bank')

    def __str__(self):
        return f"{self.bank.bank_name} - {self.card_network.network_name} (Fee Free: {self.is_fee_free})"


# ---------------------------------------------------------------------------
# 4. ATMS
# ---------------------------------------------------------------------------
class ATM(models.Model):
    """
    Represents a physical ATM machine.
    Primary coordinates are stored in latitude and longitude as defined in the ERD.
    If PostGIS/GeoDjango is available, `location` is auto-synced upon save to support
    spatial index lookups and distance calculations.
    """
    atm_id = models.BigAutoField(primary_key=True)
    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        related_name='atms',
        db_column='bank_id',
    )
    name = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    address_line = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if HAS_GIS:
        location = gis_models.PointField(srid=4326, null=True, blank=True)

    networks = models.ManyToManyField(
        CardNetwork,
        through='ATMNetwork',
        related_name='atms',
        blank=True,
    )

    class Meta:
        db_table = 'atms'
        verbose_name = _('ATM')
        verbose_name_plural = _('ATMs')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if HAS_GIS and self.latitude is not None and self.longitude is not None:
            self.location = Point(float(self.longitude), float(self.latitude), srid=4326)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bank.bank_name} — {self.name}"

    @property
    def latest_status(self):
        """Return the most recent StatusReport for this ATM, or None."""
        return self.status_reports.order_by('-created_at').first()


# ---------------------------------------------------------------------------
# 5. ATM Networks (Junction Model)
# ---------------------------------------------------------------------------
class ATMNetwork(models.Model):
    """Junction table connecting ATMs with supported Card Networks."""
    atm_network_id = models.BigAutoField(primary_key=True)
    atm = models.ForeignKey(
        ATM,
        on_delete=models.CASCADE,
        related_name='atm_networks',
        db_column='atm_id',
    )
    network = models.ForeignKey(
        CardNetwork,
        on_delete=models.CASCADE,
        related_name='atm_networks',
        db_column='network_id',
    )

    class Meta:
        db_table = 'atm_networks'
        verbose_name = _('ATM Network')
        verbose_name_plural = _('ATM Networks')
        unique_together = ('atm', 'network')

    def __str__(self):
        return f"{self.atm.name} -> {self.network.network_name}"


# ---------------------------------------------------------------------------
# 6. Status Reports
# ---------------------------------------------------------------------------
class StatusReport(models.Model):
    """
    Crowd-sourced operational status update for an ATM.
    Records whether the ATM is online and whether cash is available.
    """
    status_report_id = models.BigAutoField(primary_key=True)
    atm = models.ForeignKey(
        ATM,
        on_delete=models.CASCADE,
        related_name='status_reports',
        db_column='atm_id',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='status_reports',
        db_column='user_id',
    )
    is_online = models.BooleanField()
    has_cash = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'status_reports'
        verbose_name = _('Status Report')
        verbose_name_plural = _('Status Reports')
        ordering = ['-created_at']

    def __str__(self):
        status_text = "Online" if self.is_online else "Offline"
        cash_text = "Has Cash" if self.has_cash else "No Cash"
        return f"ATM {self.atm_id} [{status_text}, {cash_text}] by User {self.user_id} @ {self.created_at:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# 7. ATM Reports
# ---------------------------------------------------------------------------
class ATMReport(models.Model):
    """
    Crowd-sourced report for fee discrepancies, inaccurate locations, or general notes.
    """
    class ReportType(models.TextChoices):
        FEE_DISCREPANCY = 'FEE_DISCREPANCY', _('Fee Discrepancy')
        LOCATION_INACCURATE = 'LOCATION_INACCURATE', _('Location Inaccurate')
        GENERAL_NOTE = 'GENERAL_NOTE', _('General Note')

    report_id = models.BigAutoField(primary_key=True)
    atm = models.ForeignKey(
        ATM,
        on_delete=models.CASCADE,
        related_name='atm_reports',
        db_column='atm_id',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='atm_reports',
        db_column='user_id',
    )
    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
    )
    actual_fee = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'atm_reports'
        verbose_name = _('ATM Report')
        verbose_name_plural = _('ATM Reports')
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_report_type_display()}] ATM {self.atm_id} by User {self.user_id} @ {self.created_at:%Y-%m-%d %H:%M}"
