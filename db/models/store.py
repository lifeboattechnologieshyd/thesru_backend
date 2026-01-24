import uuid
from django.contrib.postgres.fields import ArrayField
from db.mixins import AuditModel
from django.db import models

from db.models import Store, User
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
    #  LSIN = Product family / PDP identifier
    lsin = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Lifeboat Standard Identification Number"
    )
    #  Group identifier for variants
    group_code = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Product family code (same for all variants)"
    )
    # SKU identity
    sku = models.CharField(max_length=30, unique=True)

    # Display
    name = models.CharField(max_length=150)
    colour = models.CharField(max_length=50)
    size = models.CharField(max_length=50, null=True, blank=True)

    # Pricing
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    gst_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    gst_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Inventory
    current_stock = models.PositiveIntegerField(default=0)

    # Discovery / PDP
    description = models.TextField(null=True, blank=True)
    highlights = models.TextField(null=True, blank=True)

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
    search_tags = ArrayField(models.CharField(max_length=50),null=True)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0
    )
    total_rating = models.PositiveIntegerField(default=0)
    number_of_reviews = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "products"
        unique_together = ("store", "group_code", "sku")
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["store", "group_code"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.colour} ({self.sku})"

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
    title = models.CharField(max_length=100,null=True)
    description = models.CharField(max_length=1000,null=True)
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
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )
    order_number = models.CharField(unique=True, max_length=50, null=False)
    address = models.JSONField()
    mrp = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    coupon_discount = models.DecimalField(decimal_places=2, max_digits=10)
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    wallet_paid = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    paid_online = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    cash_on_delivery = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    status = models.CharField(choices=OrderStatus.choices, max_length=30, default=OrderStatus.INITIATED)

    class Meta:
        db_table = "order"

class OrderProducts(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.PROTECT,
        related_name="order_items"
    )
    sku = models.CharField(max_length=20)
    qty = models.PositiveIntegerField(default=0)
    mrp = models.DecimalField(decimal_places=2, max_digits=10)
    selling_price = models.DecimalField(decimal_places=2, max_digits=10)
    apportioned_discount = models.DecimalField(decimal_places=2, max_digits=10)
    apportioned_wallet = models.DecimalField(decimal_places=2, max_digits=10)
    apportioned_online = models.DecimalField(decimal_places=2, max_digits=10)
    apportioned_gst = models.DecimalField(decimal_places=2, max_digits=10)
    rating = models.DecimalField(decimal_places=2, max_digits=10,default=0)
    review = models.BooleanField(default=False)

    class Meta:
        db_table = "order_product"



class OrderTimeLines(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="timelines"
    )
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
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    gateway = models.CharField(
        max_length=20,
        default="cashfree"
    )
    cf_order_id = models.CharField(max_length=20, null=False) #cf_order_id
    session_id = models.CharField(max_length=200, null=False)
    amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    status = models.CharField(choices=PaymentStatus.choices)

    class Meta:
        db_table = "payment"



class Cart(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(
        Store,
        null=True,
        on_delete=models.CASCADE,
        related_name="cart_items"

    )
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    is_active = models.BooleanField(default=True)


    class Meta:
        db_table = "cart"
        unique_together = (
            "store",
            "user",
            "product"
        )
        indexes = [
            models.Index(fields=["store", "user", "is_active"]),
        ]

class Wishlist(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.CASCADE,
        related_name="wishlist_items"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="wishlists"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "wishlist"
        unique_together = ("store", "user", "product")
        indexes = [
            models.Index(fields=["store", "user", "is_active"]),
            models.Index(fields=["user"]),
            models.Index(fields=["product"]),
        ]


class ProductReviews(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product,
        null=True,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    rating = models.PositiveIntegerField()
    review = models.CharField(max_length=1000, null=True, default="")

    class Meta:
        db_table = "productreviews"
        indexes = [
            models.Index(fields=["user_id"]),
            # models.Index(fields=["product_id"]),
        ]



class StoreSequence(AuditModel):
    store = models.OneToOneField(Store, on_delete=models.CASCADE)
    last_lsin_number = models.PositiveIntegerField(default=0)


class OrderSequence(AuditModel):
    store = models.OneToOneField(Store, on_delete=models.CASCADE)
    order_number = models.PositiveIntegerField(default=0)


