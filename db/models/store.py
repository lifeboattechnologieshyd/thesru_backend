from db.mixins import AuditModel
from django.db import models

class Store(AuditModel):
    name = models.CharField(max_length=50,null=True)

    class Meta:
        db_table = "store"