from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse


class Category(models.Model):
    """Categories for inventory items (e.g., Radio, Fiber, Tools, Civil Materials)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
        ('both', 'Both'),
    ], default='both')
    color = models.CharField(max_length=20, default='#3498db')  # Hex color code
    icon = models.CharField(max_length=50, default='fa-boxes')  # FontAwesome icon

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_full_name(self):
        """Get full category path (e.g., 'Electronics > Networking > Routers')"""
        if self.parent:
            return f"{self.parent.get_full_name()} > {self.name}"
        return self.name


class Location(models.Model):
    """Locations where inventory items can be stored"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
        ('both', 'Both'),
    ], default='both')

    class Meta:
        verbose_name = 'Storage Location'
        verbose_name_plural = 'Storage Locations'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Suppliers/vendors for inventory items"""
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    """Main inventory item model"""
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('used', 'Used'),
        ('refurbished', 'Refurbished'),
        ('damaged', 'Damaged'),
        ('broken', 'Broken'),
    )

    # Basic item information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, blank=True, verbose_name="SKU")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')

    # Company/ownership
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
        ('both', 'Both'),
    ], default='wisp')

    # Stock information
    quantity = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0, help_text="Minimum quantity before reordering")
    reorder_quantity = models.PositiveIntegerField(default=0, help_text="Suggested quantity to reorder")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')

    # Financial information
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      help_text="Total value of current stock")

    # Supplier information
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    supplier_part_number = models.CharField(max_length=100, blank=True)

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_ordered_date = models.DateField(null=True, blank=True)
    last_received_date = models.DateField(null=True, blank=True)
    last_counted_date = models.DateField(null=True, blank=True)

    # Status and metadata
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")

    class Meta:
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'category']),
            models.Index(fields=['quantity']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('inventory:item_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        # Calculate total value
        if self.unit_price is not None:
            self.total_value = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def is_low_stock(self):
        """Check if item is below minimum stock level"""
        return self.quantity <= self.minimum_stock

    def stock_status(self):
        """Return stock status (OK, Low, Out of Stock)"""
        if self.quantity == 0:
            return "Out of Stock"
        elif self.is_low_stock():
            return "Low Stock"
        return "OK"

    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


class StockMovement(models.Model):
    """Record of stock movements (in/out)"""
    MOVEMENT_TYPES = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('transfer', 'Transfer'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('count', 'Stock Count'),
    )

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='movements')
    quantity = models.IntegerField(help_text="Positive for stock in, negative for stock out")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    movement_date = models.DateTimeField(default=timezone.now)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Location information
    source_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_movements'
    )
    destination_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='destination_movements'
    )

    # Reference information
    reference_number = models.CharField(max_length=100, blank=True, help_text="PO number, job number, etc.")
    job_reference = models.CharField(max_length=100, blank=True, help_text="Associated job reference")
    notes = models.TextField(blank=True)

    # Stock information after movement
    stock_after = models.PositiveIntegerField(help_text="Stock level after this movement")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Unit price at time of movement")

    class Meta:
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-movement_date']
        indexes = [
            models.Index(fields=['movement_date']),
            models.Index(fields=['movement_type']),
        ]

    def __str__(self):
        if self.quantity >= 0:
            return f"{self.item.name}: +{self.quantity} ({self.get_movement_type_display()})"
        return f"{self.item.name}: {self.quantity} ({self.get_movement_type_display()})"


class StockAdjustment(models.Model):
    """Record of stock adjustments due to inventory counts or reconciliation"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='adjustments')
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    adjustment_quantity = models.IntegerField(help_text="Difference between new and previous quantities")
    adjustment_date = models.DateTimeField(default=timezone.now)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    reason = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
        ordering = ['-adjustment_date']

    def __str__(self):
        return f"{self.item.name}: adjusted by {self.adjustment_quantity}"

    def save(self, *args, **kwargs):
        # Calculate adjustment quantity if not provided
        if self.adjustment_quantity == 0:
            self.adjustment_quantity = self.new_quantity - self.previous_quantity
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    """Purchase orders for inventory items"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('partially_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    )

    order_number = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)

    # Financial information
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Tracking information
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_purchase_orders'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_orders'
    )

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    # Company/ownership
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
    ])

    # Additional information
    notes = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"PO #{self.order_number} - {self.supplier.name}"

    def get_absolute_url(self):
        return reverse('inventory:purchase_order_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        # Calculate total
        self.total = self.subtotal + self.tax + self.shipping
        super().save(*args, **kwargs)

    def is_editable(self):
        """Check if PO is still editable"""
        return self.status in ['draft', 'submitted']

    def mark_as_approved(self, approved_by):
        """Mark PO as approved"""
        if self.status == 'submitted':
            self.status = 'approved'
            self.approved_by = approved_by
            self.approved_at = timezone.now()
            self.save()

    def mark_as_ordered(self):
        """Mark PO as ordered"""
        if self.status == 'approved':
            self.status = 'ordered'
            self.order_date = timezone.now().date()
            self.save()


class PurchaseOrderItem(models.Model):
    """Line items for purchase orders"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity_ordered} x {self.item.name}"

    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)

        # Update purchase order subtotal
        po = self.purchase_order
        po.subtotal = sum(item.line_total for item in po.items.all())
        po.save()

    def is_fully_received(self):
        """Check if item is fully received"""
        return self.quantity_received >= self.quantity_ordered

    def receive_items(self, quantity, location, performed_by=None):
        """Receive items and update inventory"""
        if quantity <= 0 or quantity > (self.quantity_ordered - self.quantity_received):
            return False

        # Update received quantity
        self.quantity_received += quantity
        self.save()

        # Update item stock
        self.item.quantity += quantity
        self.item.last_received_date = timezone.now().date()
        self.item.save()

        # Create stock movement
        StockMovement.objects.create(
            item=self.item,
            quantity=quantity,
            movement_type='in',
            reference_number=f"PO #{self.purchase_order.order_number}",
            destination_location=location,
            performed_by=performed_by,
            stock_after=self.item.quantity,
            unit_price=self.unit_price
        )

        # Update purchase order status
        po = self.purchase_order
        if all(item.is_fully_received() for item in po.items.all()):
            po.status = 'fully_received'
            po.actual_delivery_date = timezone.now().date()
        else:
            po.status = 'partially_received'
        po.save()

        return True


class InventoryCount(models.Model):
    """Records of physical inventory counts"""
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    count_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    count_date = models.DateField(default=timezone.now)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    company = models.CharField(max_length=10, choices=[
        ('wisp', 'WISP'),
        ('fno', 'FNO'),
        ('both', 'Both'),
    ])
    notes = models.TextField(blank=True)

    # Tracking information
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_inventory_counts'
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_inventory_counts'
    )

    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Inventory Count'
        verbose_name_plural = 'Inventory Counts'
        ordering = ['-count_date']

    def __str__(self):
        return f"Count #{self.count_reference} - {self.count_date}"

    def get_absolute_url(self):
        return reverse('inventory:count_detail', kwargs={'pk': self.pk})

    def mark_as_completed(self, completed_by):
        """Mark count as completed and process adjustments"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.completed_by = completed_by
            self.completed_at = timezone.now()
            self.save()

            # Process count items and create adjustments
            for count_item in self.items.all():
                item = count_item.item
                previous_quantity = item.quantity

                # Create adjustment if there's a discrepancy
                if count_item.counted_quantity != previous_quantity:
                    # Create stock adjustment
                    adjustment = StockAdjustment.objects.create(
                        item=item,
                        previous_quantity=previous_quantity,
                        new_quantity=count_item.counted_quantity,
                        adjustment_quantity=count_item.counted_quantity - previous_quantity,
                        performed_by=completed_by,
                        reason=f"Inventory Count #{self.count_reference}",
                        notes=count_item.notes
                    )

                    # Create stock movement
                    movement_type = 'adjustment'
                    StockMovement.objects.create(
                        item=item,
                        quantity=adjustment.adjustment_quantity,
                        movement_type=movement_type,
                        reference_number=f"Count #{self.count_reference}",
                        source_location=self.location if adjustment.adjustment_quantity < 0 else None,
                        destination_location=self.location if adjustment.adjustment_quantity > 0 else None,
                        performed_by=completed_by,
                        stock_after=count_item.counted_quantity,
                        notes=count_item.notes
                    )

                    # Update item quantity
                    item.quantity = count_item.counted_quantity
                    item.last_counted_date = self.count_date
                    item.save()
                else:
                    # Just update the last counted date
                    item.last_counted_date = self.count_date
                    item.save()


class InventoryCountItem(models.Model):
    """Individual items in an inventory count"""
    inventory_count = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    expected_quantity = models.PositiveIntegerField(help_text="Quantity in system before count")
    counted_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Actual quantity counted")
    discrepancy = models.IntegerField(default=0, help_text="Difference between counted and expected")
    notes = models.TextField(blank=True)
    counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    counted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Inventory Count Item'
        verbose_name_plural = 'Inventory Count Items'
        ordering = ['item__name']
        unique_together = ['inventory_count', 'item']

    def __str__(self):
        return f"{self.item.name} - Expected: {self.expected_quantity}, Counted: {self.counted_quantity or 'Not counted'}"

    def save(self, *args, **kwargs):
        # Calculate discrepancy if counted
        if self.counted_quantity is not None:
            self.discrepancy = self.counted_quantity - self.expected_quantity
        super().save(*args, **kwargs)


class ItemAttachment(models.Model):
    """File attachments for inventory items"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='inventory_attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # Size in bytes
    file_type = models.CharField(max_length=100)  # MIME type
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Item Attachment'
        verbose_name_plural = 'Item Attachments'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file_name