from django.contrib import admin
from .models import (
    Category, Location, Supplier, Item, StockMovement, StockAdjustment,
    PurchaseOrder, PurchaseOrderItem, InventoryCount, InventoryCountItem, 
    ItemAttachment
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'company', 'icon')
    list_filter = ('company',)
    search_fields = ('name', 'description')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('name', 'description', 'address')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'email', 'phone')


class ItemAttachmentInline(admin.TabularInline):
    model = ItemAttachment
    extra = 1
    readonly_fields = ('file_size', 'file_type', 'uploaded_at', 'uploaded_by')


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ('movement_date', 'stock_after')
    fields = ('movement_type', 'quantity', 'reference_number', 'movement_date', 'stock_after', 'notes')
    max_num = 10
    can_delete = False


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'company', 'quantity', 'minimum_stock', 'stock_status', 'location', 'condition')
    list_filter = ('company', 'category', 'condition', 'is_active', 'location')
    search_fields = ('name', 'description', 'sku', 'tags')
    readonly_fields = ('total_value', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'sku', 'category', 'company', 'is_active', 'tags')
        }),
        ('Stock Information', {
            'fields': ('quantity', 'minimum_stock', 'reorder_quantity', 'location', 'condition')
        }),
        ('Financial Information', {
            'fields': ('unit_price', 'total_value')
        }),
        ('Supplier Information', {
            'fields': ('supplier', 'supplier_part_number')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'last_ordered_date', 'last_received_date', 'last_counted_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    inlines = [ItemAttachmentInline, StockMovementInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity', 'movement_type', 'movement_date', 'reference_number', 'performed_by')
    list_filter = ('movement_type', 'movement_date')
    search_fields = ('item__name', 'reference_number', 'job_reference', 'notes')
    date_hierarchy = 'movement_date'


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('item', 'previous_quantity', 'new_quantity', 'adjustment_quantity', 'adjustment_date', 'performed_by')
    list_filter = ('adjustment_date',)
    search_fields = ('item__name', 'reason', 'notes')
    date_hierarchy = 'adjustment_date'


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'supplier', 'company', 'status', 'order_date', 'expected_delivery_date', 'total')
    list_filter = ('status', 'company', 'supplier')
    search_fields = ('order_number', 'notes')
    readonly_fields = ('subtotal', 'total', 'created_at', 'updated_at', 'approved_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('order_number', 'supplier', 'company', 'status')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery_date', 'actual_delivery_date', 'created_at', 'updated_at', 'approved_at')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax', 'shipping', 'total')
        }),
        ('Additional Information', {
            'fields': ('notes', 'shipping_address')
        }),
        ('Tracking', {
            'fields': ('created_by', 'approved_by')
        }),
    )
    inlines = [PurchaseOrderItemInline]


class InventoryCountItemInline(admin.TabularInline):
    model = InventoryCountItem
    extra = 1
    readonly_fields = ('expected_quantity', 'discrepancy')


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ('count_reference', 'location', 'company', 'status', 'count_date', 'created_by')
    list_filter = ('status', 'company', 'location')
    search_fields = ('count_reference', 'notes')
    readonly_fields = ('created_at', 'completed_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('count_reference', 'status', 'count_date', 'location', 'company')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'completed_by', 'created_at', 'completed_at')
        }),
    )
    inlines = [InventoryCountItemInline]