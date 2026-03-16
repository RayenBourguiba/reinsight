from django.db import models
import uuid
from django.conf import settings

class Cedant(models.Model):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=2, blank=True, default="")
    external_id = models.CharField(max_length=64, blank=True, default="")

    def __str__(self):
        return self.name

class Portfolio(models.Model):
    cedant = models.ForeignKey(Cedant, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cedant.name} - {self.name}"

class Treaty(models.Model):
    QS = "QS"
    XOL = "XOL"
    TYPE_CHOICES = [(QS, "Quota Share"), (XOL, "Excess of Loss")]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="treaties")
    name = models.CharField(max_length=255)
    treaty_type = models.CharField(max_length=3, choices=TYPE_CHOICES)

    # QS
    ceded_share_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # XOL
    attachment = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

class Exposure(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="exposures")

    lob = models.CharField(max_length=32)      # PROPERTY, ENERGY...
    peril = models.CharField(max_length=32)    # FLOOD, WIND...
    country = models.CharField(max_length=2)   # FR, US...
    region = models.CharField(max_length=64, blank=True, default="")

    tiv = models.DecimalField(max_digits=18, decimal_places=2)
    premium = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    policy_id = models.CharField(max_length=64, blank=True, default="")
    location_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

class Upload(models.Model):
    STATUS_UPLOADED = "UPLOADED"
    STATUS_PARSED = "PARSED"
    STATUS_FAILED = "FAILED"
    STATUS_CHOICES = [
        (STATUS_UPLOADED, "Uploaded"),
        (STATUS_PARSED, "Parsed"),
        (STATUS_FAILED, "Failed"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128, blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_UPLOADED)
    error_message = models.TextField(blank=True, default="")
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)