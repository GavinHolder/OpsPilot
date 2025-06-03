from django import forms
from django.utils import timezone
from .models import (
    Category, Location, Supplier, Item, StockMovement, StockAdjustment,
    PurchaseOrder, PurchaseOrderItem, InventoryCount, InventoryCountItem,
    ItemAttachment
)


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories"""

    class Meta:
        model = Category
        fields = ['name', 'description', 'parent', 'company', 'color', 'icon']


class LocationForm(forms.ModelForm):
    """Form for creating and editing storage locations"""

    class Meta:
        model = Location
        fields = ['name', 'description', 'address', 'company', 'is_active']


class SupplierForm(forms.ModelForm):
    """Form for creating and editing suppliers"""

    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'website', 'notes', 'is_active']


class ItemForm(forms.ModelForm):
    """Form for creating and editing inventory items"""

    class Meta:
        model = Item
        fields = [
            'name', 'description', 'sku', 'category', 'company',
            'quantity', 'minimum_stock', 'reorder_quantity', 'location', 'condition',
            'unit_price', 'supplier', 'supplier_part_number', 'is_active', 'notes', 'tags'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.TextInput(attrs={'placeholder': 'Comma-separated tags'}),
        }


class ItemAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to inventory items"""

    class Meta:
        model = ItemAttachment
        fields = ['file', 'description']

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set file metadata
        if instance.file:
            instance.file_name = instance.file.name
            instance.file_size = instance.file.size
            instance.file_type = instance.file.content_type

        if commit:
            instance.save()

        return instance


class StockMovementForm(forms.ModelForm):
    """Form for recording stock movements"""

    class Meta:
        model = StockMovement
        fields = [
            'item', 'quantity', 'movement_type', 'movement_date',
            'source_location', 'destination_location',
            'reference_number', 'job_reference', 'notes'
        ]
        widgets = {
            'movement_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active items
        self.fields['item'].queryset = Item.objects.filter(is_active=True)
        # Only show active locations
        self.fields['source_location'].queryset = Location.objects.filter(is_active=True)
        self.fields['destination_location'].queryset = Location.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        quantity = cleaned_data.get('quantity')
        source = cleaned_data.get('source_location')
        destination = cleaned_data.get('destination_location')

        # Validate based on movement type
        if movement_type == 'in':
            if quantity <= 0:
                self.add_error('quantity', 'Quantity must be positive for stock in')
            if not destination:
                self.add_error('destination_location', 'Destination is required for stock in')

        elif movement_type == 'out':
            if quantity >= 0:
                self.add_error('quantity', 'Quantity must be negative for stock out')
            if not source:
                self.add_error('source_location', 'Source is required for stock out')

        elif movement_type == 'transfer':
            if quantity <= 0:
                self.add_error('quantity', 'Quantity must be positive for transfers')
            if not source:
                self.add_error('source_location', 'Source is required for transfers')
            if not destination:
                self.add_error('destination_location', 'Destination is required for transfers')

        return cleaned_data


class StockAdjustmentForm(forms.ModelForm):
    """Form for recording stock adjustments"""

    class Meta:
        model = StockAdjustment
        fields = [
            'item', 'new_quantity', 'reason', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active items
        self.fields['item'].queryset = Item.objects.filter(is_active=True)

        # If an item is selected, set the initial value for previous_quantity
        if 'item' in self.data:
            try:
                item_id = int(self.data.get('item'))
                item = Item.objects.get(id=item_id)
                self.fields['previous_quantity'] = forms.IntegerField(
                    initial=item.quantity,
                    widget=forms.NumberInput(attrs={'readonly': 'readonly'})
                )
            except (ValueError, Item.DoesNotExist):
                pass

        # If editing an existing adjustment
        if self.instance.pk:
            self.fields['previous_quantity'] = forms.IntegerField(
                initial=self.instance.previous_quantity,
                widget=forms.NumberInput(attrs={'readonly': 'readonly'})
            )

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get('item')
        new_quantity = cleaned_data.get('new_quantity')

        if item and new_quantity is not None:
            # Set previous quantity
            cleaned_data['previous_quantity'] = item.quantity

            # Calculate adjustment quantity
            cleaned_data['adjustment_quantity'] = new_quantity - item.quantity

        return cleaned_data


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating and editing purchase orders"""

    class Meta:
        model = PurchaseOrder
        fields = [
            'order_number', 'supplier', 'company', 'expected_delivery_date',
            'status', 'tax', 'shipping', 'notes', 'shipping_address'
        ]
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Only show active suppliers
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)

        # If editing an existing PO that's beyond draft, restrict editable fields
        if self.instance.pk and not self.instance.is_editable():
            for field_name in self.fields:
                if field_name != 'status':
                    self.fields[field_name].widget.attrs['readonly'] = True

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set created_by if creating a new PO
        if not instance.pk and self.user:
            instance.created_by = self.user

        if commit:
            instance.save()

        return instance


class PurchaseOrderItemForm(forms.ModelForm):
    """Form for adding items to a purchase order"""

    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'quantity_ordered', 'unit_price']

    def __init__(self, *args, **kwargs):
        self.purchase_order = kwargs.pop('purchase_order', None)
        super().__init__(*args, **kwargs)

        # Only show active items
        self.fields['item'].queryset = Item.objects.filter(is_active=True)

        # Pre-fill unit price if available
        if 'item' in self.data:
            try:
                item_id = int(self.data.get('item'))
                item = Item.objects.get(id=item_id)
                if item.unit_price and not self.data.get('unit_price'):
                    self.fields['unit_price'].initial = item.unit_price
            except (ValueError, Item.DoesNotExist):
                pass

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set purchase order if provided
        if self.purchase_order:
            instance.purchase_order = self.purchase_order

        # Calculate line total
        instance.line_total = instance.quantity_ordered * instance.unit_price

        if commit:
            instance.save()

        return instance


class InventoryCountForm(forms.ModelForm):
    """Form for creating inventory counts"""

    class Meta:
        model = InventoryCount
        fields = ['count_reference', 'count_date', 'location', 'company', 'notes']
        widgets = {
            'count_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Only show active locations
        self.fields['location'].queryset = Location.objects.filter(is_active=True)

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set created_by if creating a new count
        if not instance.pk and self.user:
            instance.created_by = self.user

        if commit:
            instance.save()

        return instance


class InventoryCountItemForm(forms.ModelForm):
    """Form for recording counted quantities in an inventory count"""

    class Meta:
        model = InventoryCountItem
        fields = ['item', 'counted_quantity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.inventory_count = kwargs.pop('inventory_count', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # If editing an existing count item
        if self.instance.pk:
            self.fields['expected_quantity'] = forms.IntegerField(
                initial=self.instance.expected_quantity,
                widget=forms.NumberInput(attrs={'readonly': 'readonly'})
            )
            self.fields['item'].widget.attrs['readonly'] = True

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set inventory count if provided
        if self.inventory_count and not instance.pk:
            instance.inventory_count = self.inventory_count

            # Set expected quantity from current item quantity
            instance.expected_quantity = instance.item.quantity

        # Calculate discrepancy
        if instance.counted_quantity is not None:
            instance.discrepancy = instance.counted_quantity - instance.expected_quantity

        # Set counted_by and counted_at
        if self.user and instance.counted_quantity is not None:
            instance.counted_by = self.user
            instance.counted_at = timezone.now()

        if commit:
            instance.save()

        return instance


class ItemFilterForm(forms.Form):
    """Form for filtering inventory items"""
    STOCK_STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('low', 'Low Stock'),
        ('out', 'Out of Stock'),
        ('ok', 'In Stock'),
    ]

    company = forms.ChoiceField(
        choices=[('', 'All Companies')] + list(Item.company.field.choices),
        required=False
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories"
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        required=False,
        empty_label="All Locations"
    )
    condition = forms.ChoiceField(
        choices=[('', 'All Conditions')] + list(Item.CONDITION_CHOICES),
        required=False
    )
    stock_status = forms.ChoiceField(
        choices=STOCK_STATUS_CHOICES,
        required=False
    )
    search = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field, (forms.CharField, forms.ChoiceField, forms.ModelChoiceField)):
                field.widget.attrs['class'] = 'form-select' if isinstance(field, (forms.ChoiceField,
                                                                                  forms.ModelChoiceField)) else 'form-control'


class StockMovementFilterForm(forms.Form):
    """Form for filtering stock movements"""
    movement_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(StockMovement.MOVEMENT_TYPES),
        required=False
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    reference = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field, (forms.CharField, forms.ChoiceField, forms.DateField)):
                field.widget.attrs['class'] = 'form-select' if isinstance(field, forms.ChoiceField) else 'form-control'


class PurchaseOrderFilterForm(forms.Form):
    """Form for filtering purchase orders"""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(PurchaseOrder.STATUS_CHOICES),
        required=False
    )
    company = forms.ChoiceField(
        choices=[('', 'All Companies')] + list(PurchaseOrder.company.field.choices),
        required=False
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        empty_label="All Suppliers"
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field, (forms.CharField, forms.ChoiceField, forms.ModelChoiceField, forms.DateField)):
                field.widget.attrs['class'] = 'form-select' if isinstance(field, (forms.ChoiceField,
                                                                                  forms.ModelChoiceField)) else 'form-control'


class ReceiveItemsForm(forms.Form):
    """Form for receiving items from a purchase order"""
    quantity = forms.IntegerField(min_value=1)
    location = forms.ModelChoiceField(queryset=Location.objects.filter(is_active=True))

    def __init__(self, *args, **kwargs):
        self.po_item = kwargs.pop('po_item', None)
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field, (forms.IntegerField, forms.ModelChoiceField)):
                field.widget.attrs['class'] = 'form-select' if isinstance(field,
                                                                          forms.ModelChoiceField) else 'form-control'

        # Set max quantity based on remaining to receive
        if self.po_item:
            remaining = self.po_item.quantity_ordered - self.po_item.quantity_received
            self.fields['quantity'].max_value = remaining
            self.fields['quantity'].help_text = f'Maximum: {remaining}'

            # If the item has a default location, preselect it
            if self.po_item.item.location:
                self.fields['location'].initial = self.po_item.item.location.pk