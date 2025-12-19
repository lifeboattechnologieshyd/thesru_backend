import uuid
from django.contrib.postgres.fields import ArrayField
from db.mixins import AuditModel
from django.db import models

from enums.store import BannerScreen, InventoryType, AddressType


class Product(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=20,unique=True)
    name = models.CharField(max_length=100)
    size = models.CharField(max_length=50,null=True)
    colour = models.CharField(max_length=50,null=True)
    inr = models.DecimalField(decimal_places=2, max_digits=10)
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    mrp_others = models.JSONField()
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price_others = models.JSONField()
    gst_percentage = models.CharField(max_length=50,null=True)
    gst_amount = models.DecimalField(decimal_places=2, max_digits=10)
    current_stock = models.PositiveIntegerField(default=0)
    images =  ArrayField(models.CharField(max_length=300), null=True)
    videos =  ArrayField(models.CharField(max_length=300), null=True)
    thumbnail_image = models.CharField(max_length=300)

    class Meta:
        db_table = "product"
        ordering = ["-created_at"]

class DisplayProduct(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    default_product_id = models.UUIDField()
    variant_product_id = ArrayField(models.CharField(max_length=50),null=True)
    is_active = models.BooleanField(default=True)
    category = ArrayField(models.CharField(max_length=50),null=True)
    gender = models.CharField(max_length=20,null=True)
    tags  = ArrayField(models.CharField(max_length=50),null=True)
    search_tags = ArrayField(models.CharField(max_length=50),null=True)
    product_name = models.CharField(max_length=100,null=True)
    product_tagline = models.CharField(max_length=100,null=True)
    age = models.PositiveIntegerField(default=0)
    description = models.TextField(null=True)
    highlights = ArrayField(models.CharField(max_length=50),null=True)
    rating = models.CharField(max_length=20,null=True)
    number_of_reviews = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = " display_product"


class Category(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=255, null=True)
    search_tags = ArrayField(models.CharField(max_length=50),null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        ordering = ["-created_at"]


class Inventory(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.UUIDField()
    sku = models.CharField(max_length=20)
    type = models.CharField(max_length=20,choices=InventoryType.choices)
    date = models.DateTimeField()
    user = models.UUIDField()
    quantity = models.PositiveIntegerField(default=0)
    quantity_before = models.PositiveIntegerField(default=0)
    quantity_after = models.PositiveIntegerField(default=0)
    purchase_rate_per_item = models.DecimalField(decimal_places=2,max_digits=10)
    purchase_price = models.DecimalField(decimal_places=2,max_digits=10)
    sale_rate_per_item = models.DecimalField(decimal_places=2,max_digits=10)
    sale_price = models.DecimalField(decimal_places=2,max_digits=10)
    gst_input = models.DecimalField(decimal_places=2,max_digits=10)
    gst_output = models.DecimalField(decimal_places=2,max_digits=10)
    remarks = models.CharField(max_length=100,null=True)

    class Meta:
        db_table = "inventory"
        ordering = ["-created_at"]



class Banner(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    screen = models.CharField(max_length=20,choices=BannerScreen.choices)
    image = models.CharField(max_length=300, null=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1)
    action = models.BooleanField(default=False)
    destination = models.JSONField()

    class Meta:
        db_table = "banner"
        ordering = ["-created_at"]


class AddressMaster(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    mobile = models.CharField(max_length=20,null=True)
    name = models.CharField(max_length=100)
    address_name = models.CharField(max_length=50)
    address_type = models.CharField(max_length=20,choices=AddressType.choices)
    full_address = models.JSONField()
    house_number = models.CharField(max_length=50)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    state_name = models.CharField(max_length=25)
    area_name = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    landmark = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "address"
        ordering = ["-created_at"]

