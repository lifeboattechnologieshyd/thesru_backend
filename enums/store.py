from django.db import models



class BannerScreen(models.TextChoices):
    HOME = "Home"
    WISHLIST = "Wishlist"

class InventoryType(models.TextChoices):
    PURCHASE = "Purchase"
    SELL = "Sell"
    PurchaseReturn = "Purchase_return"
    SaleReturn = "Sale_return"


class AddressType(models.TextChoices):
    HOME = "Home"
    OFFICE = "Office"


class PaymentStatus(models.TextChoices):
    INITIATED = "INITIATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"

class OrderStatus(models.TextChoices):
    INITIATED = "Initiated"
    PLACED = "Placed"
    FAILED = "Failed"
    CONFIRMED = "Confirmed"
    PACKED = "Packed" # after this address change for this order won't be there  from here on
    SHIPPED = "Shipped" # shipping details like partner name, url, id, expected_delivery_date,
    OUT_FOR_DELIVERY = "Outfordelivery" # we are not using this.
    DELIVERED = "Delivered" # manual for now
    RETURN_REQUESTED = "Returnrequested"
    RETURNED = "Returned"
    REFUNDED = "Refunded"
    UNFULFILLED = "Unfulfilled"
    CANCELLED = "Cancelled"
