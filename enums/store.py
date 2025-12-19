from django.db import models



class BannerScreen(models.TextChoices):
    HOME = "Home"

class InventoryType(models.TextChoices):
    PURCHASE = "Purchase"
    SELL = "Sell"
    PurchaseReturn = "Purchase_return"
    SaleReturn = "Sale_return"


class AddressType(models.TextChoices):
    HOME = "Home"
    OFFICE = "Office"