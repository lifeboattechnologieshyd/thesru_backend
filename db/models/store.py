import uuid
from django.contrib.postgres.fields import ArrayField
from db.mixins import AuditModel
from django.db import models

from enums.store import BannerScreen, InventoryType, AddressType, OrderStatus, PaymentStatus


class Product(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    sku = models.CharField(max_length=20,unique=True)
    name = models.CharField(max_length=100)
    size = models.CharField(max_length=50,null=True)
    colour = models.CharField(max_length=50,null=True)
    inr = models.DecimalField(decimal_places=2, max_digits=10,null=True)
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    mrp_others = models.JSONField(null=True)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price_others = models.JSONField(null=True)
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
    store_id = models.UUIDField()
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
        db_table = "display_product"


class Category(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=255, null=True)
    search_tags = ArrayField(models.CharField(max_length=50),null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        ordering = ["-created_at"]


class Inventory(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
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
    store_id = models.UUIDField()
    screen = models.CharField(max_length=20,choices=BannerScreen.choices)
    image = models.CharField(max_length=300, null=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1)
    action = models.BooleanField(default=False)
    destination = models.JSONField()

    class Meta:
        db_table = "banner"
        ordering = ["-created_at"]

class WebBanner(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    screen = models.CharField(max_length=20,choices=BannerScreen.choices)
    image = models.CharField(max_length=300, null=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1)
    action = models.BooleanField(default=False)
    destination = models.JSONField()

    class Meta:
        db_table = "web_banner"
        ordering = ["-created_at"]

class FlashSaleBanner(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    name = models.CharField(max_length=50,null=True)
    title = models.CharField(max_length=100,null=True)
    description = models.CharField(max_length=1000,null=True)
    screen = models.CharField(max_length=20,choices=BannerScreen.choices)
    image = models.CharField(max_length=300, null=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1)
    action = models.BooleanField(default=False)
    destination = models.JSONField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    product_id = ArrayField(models.CharField(max_length=50),null=True)
    discount = models.CharField(max_length=20)


    class Meta:
        db_table = "flash_sale_banner"
        ordering = ["-created_at"]

class AddressMaster(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    user_id = models.UUIDField()
    mobile = models.CharField(max_length=20,null=True)
    name = models.CharField(max_length=100)
    address_name = models.CharField(max_length=50)
    address_type = models.CharField(max_length=20,choices=AddressType.choices)
    full_address = models.CharField(max_length=100)
    house_number = models.CharField(max_length=50)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=25)
    area = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=10)
    landmark = models.CharField(max_length=100,null=True,blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "address"
        ordering = ["-created_at"]

class PinCode(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pin = models.PositiveIntegerField(unique=True)
    state = models.CharField(max_length=25)
    area = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)



    class Meta:
        db_table = "pincode"


class Order(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    user_id = models.UUIDField()
    order_id = models.CharField(unique=True, max_length=16, null=False)
    address = models.JSONField()
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    coupon_discount = models.DecimalField(decimal_places=2, max_digits=10)
    wallet_paid = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    paid_online = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    cash_on_delivery = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    status = models.CharField(choices=OrderStatus.choices)

    class Meta:
        db_table = "order"

class OrderProducts(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    order_id = models.CharField(max_length=16, null=False)
    product_id = models.UUIDField(null=False)
    sku = models.CharField(max_length=20,unique=True)
    qty = models.PositiveIntegerField(default=0)
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_discount = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_wallet = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_online = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_gst = models.DecimalField(decimal_places=2, max_digits=10)
    rating = models.DecimalField(decimal_places=2, max_digits=10)
    review = models.BooleanField(default=False)

    class Meta:
        db_table = "order_product"



class OrderTimeLines(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    order_id = models.CharField(max_length=16, null=False)
    status = models.CharField(max_length=16, null=False)
    remarks = models.CharField(max_length=250, null=True)

    class Meta:
        db_table = "order_timeline"


class OrderShippingDetails(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=16, null=False)
    courier_service = models.CharField(max_length=16, null=False)
    tracking_id = models.CharField(max_length=250, null=False)
    tracking_url = models.CharField(max_length=250, null=False)
    estimated_delivery_date = models.CharField(max_length=250, null=False)
    remarks = models.CharField(max_length=1000, null=True)

    class Meta:
        db_table = "order_shipping_details"


class Payment(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    order_id = models.CharField(max_length=16, null=False)
    txn_id = models.CharField(max_length=16, null=False) #cf_order_id
    session_id = models.CharField(max_length=16, null=False)
    amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    status = models.CharField(choices=PaymentStatus.choices)
    user_id = models.UUIDField(null=False)
    mobile = models.CharField(null=False)
    email = models.CharField(null=True)

    class Meta:
        db_table = "payment"


class CashFree(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField(null=True)
    client_id = models.CharField(null=False, unique=True)
    client_secret = models.CharField(null=False, unique=True)
    webhook = models.CharField(max_length=100)
    url = models.CharField(max_length=100)

    class Meta:
        db_table = "cashfree"


class Cart(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    product_id = models.UUIDField()
    quantity = models.PositiveIntegerField()
    user_id = models.UUIDField()

    class Meta:
        db_table = "cart"
        unique_together = ("user_id", "product_id")
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["product_id"]),
        ]

class Wishlist(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    product_id = models.UUIDField()
    user_id = models.UUIDField(null=False)

    class Meta:
        db_table = "wishlist"

        unique_together = ("user_id", "product_id")
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["product_id"]),
        ]





