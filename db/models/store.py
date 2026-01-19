import uuid
from django.contrib.postgres.fields import ArrayField
from db.mixins import AuditModel
from django.db import models

from db.models import Store
from enums.store import BannerScreen, InventoryType, AddressType, OrderStatus, PaymentStatus


class Tag(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="tags"
    )
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tags"
        unique_together = ("store", "slug")


class Category(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="categories"
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60)
    icon = models.CharField(max_length=255, null=True)
    search_tags = ArrayField(models.CharField(max_length=50),null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "name"],
                name="unique_category_per_store"
            )
        ]

        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.store})"


class Product(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="products"
    )
    sku = models.CharField(max_length=20,unique=True)
    name = models.CharField(max_length=100)
    size = models.CharField(max_length=50,null=True)
    colour = models.CharField(max_length=50,null=True)
    is_active = models.BooleanField(default=True)
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)

    gst_percentage = models.CharField(max_length=50,null=True)
    gst_amount = models.DecimalField(decimal_places=2, max_digits=10)
    current_stock = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["sku"]),
        ]

    def __str__(self):
        return self.sku
class ProductMedia(AuditModel):
    IMAGE = "image"
    VIDEO = "video"

    MEDIA_TYPE_CHOICES = (
        (IMAGE, "Image"),
        (VIDEO, "Video"),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="media"
    )

    url = models.CharField(max_length=300)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "product_media"
        ordering = ["position"]


class ProductVariant(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lsin = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        help_text="Lifeboat standard identification number. Business-facing display product ID"
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="display_products"
    )
    default_product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="as_default_variant"
    )

    products = models.ManyToManyField(
        Product,
        related_name="variant_groups",
        help_text="All SKU products belonging to this display product"
    )

    categories = models.ManyToManyField(
        Category,
        related_name="display_products",
        blank=True
    )

    tags = models.ManyToManyField(
        Tag,
        related_name="display_products",
        blank=True
    )
    is_active = models.BooleanField(default=True)
    gender = models.CharField(max_length=20,null=True)
    search_tags = ArrayField(models.CharField(max_length=50),null=True)
    display_name = models.CharField(max_length=200,null=True)
    display_info = models.CharField(max_length=200,null=True)
    description = models.TextField(null=True)
    highlights = models.TextField(null=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0
    )
    total_rating = models.PositiveIntegerField(default=0)
    number_of_reviews = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product_variants"
        indexes = [
            models.Index(fields=["store", "is_active"]),
        ]

    def __str__(self):
        return self.display_name


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
    order_id = models.CharField(unique=True, max_length=50, null=False)
    address = models.JSONField()
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    coupon_discount = models.DecimalField(decimal_places=2, max_digits=10)
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    wallet_paid = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    paid_online = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    cash_on_delivery = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    status = models.CharField(choices=OrderStatus.choices)

    class Meta:
        db_table = "order"

class OrderProducts(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    order_id = models.CharField(max_length=50, null=False)
    product = models.ForeignKey(
        ProductVariant,
        null=True,
        on_delete=models.PROTECT,
        related_name="order_items"
    )
    sku = models.CharField(max_length=20)
    qty = models.PositiveIntegerField(default=0)
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_discount = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_wallet = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_online = models.DecimalField(decimal_places=2, max_digits=10)
    Apportioned_gst = models.DecimalField(decimal_places=2, max_digits=10)
    rating = models.DecimalField(decimal_places=2, max_digits=10,default=0)
    review = models.BooleanField(default=False)

    class Meta:
        db_table = "order_product"



class OrderTimeLines(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    order_id = models.CharField(max_length=50, null=False)
    status = models.CharField(max_length=20, null=False)
    remarks = models.CharField(max_length=250, null=True)

    class Meta:
        db_table = "order_timeline"


class OrderShippingDetails(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=50, null=False)
    courier_service = models.CharField(max_length=50, null=False)
    tracking_id = models.CharField(max_length=250, null=False)
    tracking_url = models.CharField(max_length=250, null=False)
    estimated_delivery_date = models.CharField(max_length=250, null=False)
    remarks = models.CharField(max_length=1000, null=True)

    class Meta:
        db_table = "order_shipping_details"


class Payment(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    order_id = models.CharField(max_length=20, null=False)
    txn_id = models.CharField(max_length=20, null=False) #cf_order_id
    session_id = models.CharField(max_length=200, null=False)
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
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    quantity = models.PositiveIntegerField()
    user_id = models.UUIDField()

    class Meta:
        db_table = "cart"
        # unique_together = ("user_id", "product_id")
        # indexes = [
        #     models.Index(fields=["user_id"]),
        #     models.Index(fields=["product_id"]),
        # ]

class Wishlist(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.CASCADE,
        related_name="wishlist_items"
    )
    user_id = models.UUIDField(null=False)

    class Meta:
        db_table = "wishlist"

        # unique_together = ("user_id", "product_id")
        # indexes = [
        #     models.Index(fields=["user_id"]),
        #     models.Index(fields=["product_id"]),
        # ]


class ProductReviews(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_id = models.UUIDField()
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    user_id = models.UUIDField(null=False)
    username = models.CharField(max_length=30,null=False, default="System")
    rating = models.PositiveIntegerField()
    review = models.CharField(max_length=1000, null=True, default="")

    class Meta:
        db_table = "productreviews"
        indexes = [
            models.Index(fields=["user_id"]),
            # models.Index(fields=["product_id"]),
        ]






