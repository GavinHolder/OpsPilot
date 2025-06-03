# inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Sum, F, Count, Case, When, Func
from django.contrib import messages
from django.db import transaction, models

from .models import (
    Category, Location, Supplier, Item, StockMovement, StockAdjustment,
    PurchaseOrder, PurchaseOrderItem, InventoryCount, InventoryCountItem,
    ItemAttachment
)
from .forms import (
    CategoryForm, LocationForm, SupplierForm, ItemForm, ItemAttachmentForm,
    StockMovementForm, StockAdjustmentForm, PurchaseOrderForm, PurchaseOrderItemForm,
    InventoryCountForm, InventoryCountItemForm, ItemFilterForm,
    StockMovementFilterForm, PurchaseOrderFilterForm, ReceiveItemsForm
)


# Item Views
@method_decorator(login_required, name='dispatch')
class ItemListView(ListView):
    """View for listing inventory items with filtering"""
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 50

    def get_queryset(self):
        queryset = Item.objects.all()

        # Apply filters from form
        form = ItemFilterForm(self.request.GET)
        if form.is_valid():
            data = form.cleaned_data

            # Filter by company
            if data.get('company'):
                queryset = queryset.filter(company=data['company'])

            # Filter by category
            if data.get('category'):
                queryset = queryset.filter(category=data['category'])

            # Filter by location
            if data.get('location'):
                queryset = queryset.filter(location=data['location'])

            # Filter by condition
            if data.get('condition'):
                queryset = queryset.filter(condition=data['condition'])

            # Filter by stock status
            if data.get('stock_status'):
                if data['stock_status'] == 'low':
                    queryset = queryset.filter(quantity__gt=0, quantity__lte=F('minimum_stock'))
                elif data['stock_status'] == 'out':
                    queryset = queryset.filter(quantity=0)
                elif data['stock_status'] == 'ok':
                    queryset = queryset.filter(quantity__gt=F('minimum_stock'))

            # Search in name, description, sku, tags
            if data.get('search'):
                search_term = data['search']
                queryset = queryset.filter(
                    Q(name__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(sku__icontains=search_term) |
                    Q(tags__icontains=search_term)
                )

        # Only show active items by default, unless filtered
        if 'is_active' not in self.request.GET:
            queryset = queryset.filter(is_active=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ItemFilterForm(self.request.GET)

        # Add summary statistics
        context['total_items'] = Item.objects.filter(is_active=True).count()
        context['low_stock_count'] = Item.objects.filter(
            is_active=True,
            quantity__gt=0,
            quantity__lte=F('minimum_stock')
        ).count()
        context['out_of_stock_count'] = Item.objects.filter(
            is_active=True,
            quantity=0
        ).count()

        # Stock value by company
        context['wisp_stock_value'] = Item.objects.filter(
            company='wisp',
            is_active=True
        ).exclude(
            total_value=None
        ).aggregate(total=Sum('total_value'))['total'] or 0

        context['fno_stock_value'] = Item.objects.filter(
            company='fno',
            is_active=True
        ).exclude(
            total_value=None
        ).aggregate(total=Sum('total_value'))['total'] or 0

        return context


@method_decorator(login_required, name='dispatch')
class ItemDetailView(DetailView):
    """View for viewing inventory item details"""
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get related data
        context['movements'] = StockMovement.objects.filter(item=self.object).order_by('-movement_date')[:10]
        context['adjustments'] = StockAdjustment.objects.filter(item=self.object).order_by('-adjustment_date')[:5]
        context['attachments'] = self.object.attachments.all()

        # Add form for adding attachments
        context['attachment_form'] = ItemAttachmentForm()

        return context


@method_decorator(login_required, name='dispatch')
class ItemCreateView(CreateView):
    """View for creating new inventory items"""
    model = Item
    form_class = ItemForm
    template_name = 'inventory/item_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Item created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ItemUpdateView(UpdateView):
    """View for updating inventory items"""
    model = Item
    form_class = ItemForm
    template_name = 'inventory/item_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Item updated successfully!')
        return super().form_valid(form)


@login_required
@require_POST
def add_item_attachment(request, pk):
    """Add an attachment to an inventory item"""
    item = get_object_or_404(Item, pk=pk)
    form = ItemAttachmentForm(request.POST, request.FILES)

    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.item = item
        attachment.uploaded_by = request.user
        attachment.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the attachments section
            return render(
                request,
                'inventory/partials/attachment_item.html',
                {'attachment': attachment}
            )

        messages.success(request, 'Attachment added successfully!')
        return redirect('inventory:item_detail', pk=item.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding attachment!')
    return redirect('inventory:item_detail', pk=item.pk)


# Stock Movement Views
@method_decorator(login_required, name='dispatch')
class StockMovementListView(ListView):
    """View for listing stock movements with filtering"""
    model = StockMovement
    template_name = 'inventory/movement_list.html'
    context_object_name = 'movements'
    paginate_by = 50

    def get_queryset(self):
        queryset = StockMovement.objects.all()

        # Apply filters from form
        form = StockMovementFilterForm(self.request.GET)
        if form.is_valid():
            data = form.cleaned_data

            # Filter by movement type
            if data.get('movement_type'):
                queryset = queryset.filter(movement_type=data['movement_type'])

            # Filter by date range
            if data.get('date_from'):
                queryset = queryset.filter(movement_date__date__gte=data['date_from'])

            if data.get('date_to'):
                queryset = queryset.filter(movement_date__date__lte=data['date_to'])

            # Filter by reference
            if data.get('reference'):
                queryset = queryset.filter(
                    Q(reference_number__icontains=data['reference']) |
                    Q(job_reference__icontains=data['reference'])
                )

        return queryset.order_by('-movement_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = StockMovementFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class StockMovementCreateView(CreateView):
    """View for creating stock movements"""
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'inventory/movement_form.html'
    success_url = reverse_lazy('inventory:movement_list')

    def form_valid(self, form):
        with transaction.atomic():
            movement = form.save(commit=False)
            movement.performed_by = self.request.user

            # Update item quantity based on movement type
            item = movement.item
            original_quantity = item.quantity

            if movement.movement_type == 'in':
                item.quantity += movement.quantity
            elif movement.movement_type == 'out':
                # Ensure we have enough stock
                if item.quantity < abs(movement.quantity):
                    form.add_error('quantity', 'Not enough stock available')
                    return self.form_invalid(form)
                item.quantity += movement.quantity  # movement.quantity is negative
            elif movement.movement_type == 'transfer':
                # For transfers, we just track the movement but don't change total quantity
                pass
            elif movement.movement_type in ['adjustment', 'count']:
                # For adjustments and counts, we use the quantity as the new value
                item.quantity = movement.quantity

            # Update stock after value
            movement.stock_after = item.quantity

            # Save item and movement
            item.save()
            movement.save()

            messages.success(self.request, 'Stock movement recorded successfully!')
            return redirect(self.success_url)


# Stock Adjustment Views
@method_decorator(login_required, name='dispatch')
class StockAdjustmentCreateView(CreateView):
    """View for creating stock adjustments"""
    model = StockAdjustment
    form_class = StockAdjustmentForm
    template_name = 'inventory/adjustment_form.html'
    success_url = reverse_lazy('inventory:adjustment_list')

    def form_valid(self, form):
        with transaction.atomic():
            adjustment = form.save(commit=False)
            adjustment.performed_by = self.request.user
            adjustment.previous_quantity = adjustment.item.quantity
            adjustment.adjustment_quantity = adjustment.new_quantity - adjustment.previous_quantity

            # Save adjustment
            adjustment.save()

            # Update item quantity
            item = adjustment.item
            item.quantity = adjustment.new_quantity
            item.last_counted_date = timezone.now().date()
            item.save()

            # Create corresponding stock movement
            StockMovement.objects.create(
                item=item,
                quantity=adjustment.adjustment_quantity,
                movement_type='adjustment',
                movement_date=adjustment.adjustment_date,
                performed_by=self.request.user,
                reference_number=f"Adjustment #{adjustment.pk}",
                notes=adjustment.reason,
                stock_after=adjustment.new_quantity
            )

            messages.success(self.request, 'Stock adjustment recorded successfully!')
            return redirect(self.success_url)


@method_decorator(login_required, name='dispatch')
class StockAdjustmentListView(ListView):
    """View for listing stock adjustments"""
    model = StockAdjustment
    template_name = 'inventory/adjustment_list.html'
    context_object_name = 'adjustments'
    paginate_by = 50
    ordering = ['-adjustment_date']


# Purchase Order Views
@method_decorator(login_required, name='dispatch')
class PurchaseOrderListView(ListView):
    """View for listing purchase orders with filtering"""
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = PurchaseOrder.objects.all()

        # Apply filters from form
        form = PurchaseOrderFilterForm(self.request.GET)
        if form.is_valid():
            data = form.cleaned_data

            # Filter by status
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])

            # Filter by company
            if data.get('company'):
                queryset = queryset.filter(company=data['company'])

            # Filter by supplier
            if data.get('supplier'):
                queryset = queryset.filter(supplier=data['supplier'])

            # Filter by date range
            if data.get('date_from'):
                queryset = queryset.filter(order_date__gte=data['date_from'])

            if data.get('date_to'):
                queryset = queryset.filter(order_date__lte=data['date_to'])

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PurchaseOrderFilterForm(self.request.GET)

        # Add summary counts by status
        for status_code, status_name in PurchaseOrder.STATUS_CHOICES:
            context[f'{status_code}_count'] = PurchaseOrder.objects.filter(status=status_code).count()

        return context


@method_decorator(login_required, name='dispatch')
class PurchaseOrderDetailView(DetailView):
    """View for viewing purchase order details"""
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_detail.html'
    context_object_name = 'purchase_order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if PO is still editable
        context['is_editable'] = self.object.is_editable()

        # Add form for adding items if PO is editable
        if context['is_editable']:
            context['item_form'] = PurchaseOrderItemForm(purchase_order=self.object)

        # Add form for receiving items if PO is ordered or partially received
        if self.object.status in ['ordered', 'partially_received']:
            context['can_receive'] = True

        return context


@method_decorator(login_required, name='dispatch')
class PurchaseOrderCreateView(CreateView):
    """View for creating new purchase orders"""
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Purchase order created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class PurchaseOrderUpdateView(UpdateView):
    """View for updating purchase orders"""
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Purchase order updated successfully!')
        return super().form_valid(form)


@login_required
@require_POST
def add_purchase_order_item(request, pk):
    """Add an item to a purchase order"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)

    # Check if PO is still editable
    if not purchase_order.is_editable():
        messages.error(request, 'This purchase order can no longer be edited')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)

    form = PurchaseOrderItemForm(request.POST, purchase_order=purchase_order)

    if form.is_valid():
        po_item = form.save(commit=False)
        po_item.purchase_order = purchase_order
        po_item.save()

        # Update purchase order subtotal and total
        purchase_order.subtotal = purchase_order.items.aggregate(total=Sum('line_total'))['total'] or 0
        purchase_order.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the items section
            return render(
                request,
                'inventory/partials/purchase_order_item.html',
                {'item': po_item, 'is_editable': purchase_order.is_editable()}
            )

        messages.success(request, 'Item added successfully!')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding item!')
    return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)


@login_required
@require_POST
def remove_purchase_order_item(request, pk):
    """Remove an item from a purchase order"""
    po_item = get_object_or_404(PurchaseOrderItem, pk=pk)
    purchase_order = po_item.purchase_order

    # Check if PO is still editable
    if not purchase_order.is_editable():
        messages.error(request, 'This purchase order can no longer be edited')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)

    # Delete the item
    po_item.delete()

    # Update purchase order subtotal and total
    purchase_order.subtotal = purchase_order.items.aggregate(total=Sum('line_total'))['total'] or 0
    purchase_order.save()

    messages.success(request, 'Item removed successfully!')
    return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)


@login_required
@require_POST
def approve_purchase_order(request, pk):
    """Approve a purchase order"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)

    # Check if PO is in submitted status
    if purchase_order.status != 'submitted':
        messages.error(request, 'This purchase order cannot be approved')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)

    # Approve the PO
    purchase_order.mark_as_approved(request.user)

    messages.success(request, 'Purchase order approved successfully!')
    return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)


@login_required
@require_POST
def mark_as_ordered(request, pk):
    """Mark a purchase order as ordered"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)

    # Check if PO is in approved status
    if purchase_order.status != 'approved':
        messages.error(request, 'This purchase order cannot be marked as ordered')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)

    # Mark as ordered
    purchase_order.mark_as_ordered()

    messages.success(request, 'Purchase order marked as ordered successfully!')
    return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)


@login_required
def receive_purchase_order_item(request, pk):
    """Receive items for a purchase order item"""
    po_item = get_object_or_404(PurchaseOrderItem, pk=pk)
    purchase_order = po_item.purchase_order

    # Check if PO is in ordered or partially received status
    if purchase_order.status not in ['ordered', 'partially_received']:
        messages.error(request, 'This purchase order cannot receive items')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)

    if request.method == 'POST':
        form = ReceiveItemsForm(request.POST, po_item=po_item)

        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            location = form.cleaned_data['location']

            # Receive the items
            success = po_item.receive_items(quantity, location, request.user)

            if success:
                messages.success(request, 'Items received successfully!')
            else:
                messages.error(request, 'Error receiving items!')

            return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = ReceiveItemsForm(po_item=po_item)

    context = {
        'form': form,
        'po_item': po_item,
        'purchase_order': purchase_order
    }

    return render(request, 'inventory/receive_items_form.html', context)


# Inventory Count Views
@method_decorator(login_required, name='dispatch')
class InventoryCountListView(ListView):
    """View for listing inventory counts"""
    model = InventoryCount
    template_name = 'inventory/count_list.html'
    context_object_name = 'counts'
    paginate_by = 20
    ordering = ['-count_date']


@method_decorator(login_required, name='dispatch')
class InventoryCountDetailView(DetailView):
    """View for viewing inventory count details"""
    model = InventoryCount
    template_name = 'inventory/count_detail.html'
    context_object_name = 'count'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if count is still in progress
        context['is_in_progress'] = self.object.status == 'in_progress'

        # Add form for recording counted quantities if count is in progress
        if context['is_in_progress']:
            context['item_form'] = InventoryCountItemForm(inventory_count=self.object, user=self.request.user)

        return context


@method_decorator(login_required, name='dispatch')
class InventoryCountCreateView(CreateView):
    """View for creating new inventory counts"""
    model = InventoryCount
    form_class = InventoryCountForm
    template_name = 'inventory/count_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            inventory_count = form.save()

            # Generate a count reference if not provided
            if not inventory_count.count_reference:
                inventory_count.count_reference = f"COUNT-{inventory_count.pk}"
                inventory_count.save()

            messages.success(self.request, 'Inventory count created successfully!')
            return redirect('inventory:count_detail', pk=inventory_count.pk)


@login_required
@require_POST
def add_inventory_count_item(request, pk):
    """Add an item to an inventory count"""
    inventory_count = get_object_or_404(InventoryCount, pk=pk)

    # Check if count is still in progress
    if inventory_count.status != 'in_progress':
        messages.error(request, 'This inventory count is no longer in progress')
        return redirect('inventory:count_detail', pk=inventory_count.pk)

    form = InventoryCountItemForm(request.POST, inventory_count=inventory_count, user=request.user)

    if form.is_valid():
        count_item = form.save(commit=False)
        count_item.inventory_count = inventory_count

        # Check if item already exists in this count
        existing_item = inventory_count.items.filter(item=count_item.item).first()
        if existing_item:
            messages.error(request, 'This item is already in the count')
            return redirect('inventory:count_detail', pk=inventory_count.pk)

        # Set expected quantity from current item quantity
        count_item.expected_quantity = count_item.item.quantity
        count_item.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the items section
            return render(
                request,
                'inventory/partials/count_item.html',
                {'item': count_item, 'is_in_progress': True}
            )

        messages.success(request, 'Item added successfully!')
        return redirect('inventory:count_detail', pk=inventory_count.pk)

    # If form invalid
    if request.headers.get('HX-Request'):
        return HttpResponse(status=400)

    messages.error(request, 'Error adding item!')
    return redirect('inventory:count_detail', pk=inventory_count.pk)


@login_required
@require_POST
def update_count_item(request, pk):
    """Update the counted quantity for an inventory count item"""
    count_item = get_object_or_404(InventoryCountItem, pk=pk)
    inventory_count = count_item.inventory_count

    # Check if count is still in progress
    if inventory_count.status != 'in_progress':
        messages.error(request, 'This inventory count is no longer in progress')
        return redirect('inventory:count_detail', pk=inventory_count.pk)

    # Update the counted quantity
    try:
        counted_quantity = int(request.POST.get('counted_quantity', 0))
        notes = request.POST.get('notes', '')

        count_item.counted_quantity = counted_quantity
        count_item.notes = notes
        count_item.counted_by = request.user
        count_item.counted_at = timezone.now()
        count_item.save()

        if request.headers.get('HX-Request'):
            # Return HTML for HTMX to update the item
            return render(
                request,
                'inventory/partials/count_item.html',
                {'item': count_item, 'is_in_progress': True}
            )

        messages.success(request, 'Count updated successfully!')
        return redirect('inventory:count_detail', pk=inventory_count.pk)

    except (ValueError, TypeError):
        if request.headers.get('HX-Request'):
            return HttpResponse(status=400)

        messages.error(request, 'Invalid quantity provided')
        return redirect('inventory:count_detail', pk=inventory_count.pk)


@login_required
@require_POST
def complete_inventory_count(request, pk):
    """Mark an inventory count as completed and process adjustments"""
    inventory_count = get_object_or_404(InventoryCount, pk=pk)

    # Check if count is still in progress
    if inventory_count.status != 'in_progress':
        messages.error(request, 'This inventory count is already completed or cancelled')
        return redirect('inventory:count_detail', pk=inventory_count.pk)

    # Check if all items have been counted
    uncounted_items = inventory_count.items.filter(counted_quantity=None)
    if uncounted_items.exists():
        messages.error(request, 'All items must be counted before completing the count')
        return redirect('inventory:count_detail', pk=inventory_count.pk)

    # Complete the count
    inventory_count.mark_as_completed(request.user)

    messages.success(request, 'Inventory count completed successfully!')
    return redirect('inventory:count_detail', pk=inventory_count.pk)


# Category Views
@method_decorator(login_required, name='dispatch')
class CategoryListView(ListView):
    """View for listing categories"""
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'


@method_decorator(login_required, name='dispatch')
class CategoryCreateView(CreateView):
    """View for creating new categories"""
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CategoryUpdateView(UpdateView):
    """View for updating categories"""
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)


# Location Views
@method_decorator(login_required, name='dispatch')
class LocationListView(ListView):
    """View for listing storage locations"""
    model = Location
    template_name = 'inventory/location_list.html'
    context_object_name = 'locations'


@method_decorator(login_required, name='dispatch')
class LocationCreateView(CreateView):
    """View for creating new storage locations"""
    model = Location
    form_class = LocationForm
    template_name = 'inventory/location_form.html'
    success_url = reverse_lazy('inventory:location_list')

    def form_valid(self, form):
        messages.success(self.request, 'Location created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class LocationUpdateView(UpdateView):
    """View for updating storage locations"""
    model = Location
    form_class = LocationForm
    template_name = 'inventory/location_form.html'
    success_url = reverse_lazy('inventory:location_list')

    def form_valid(self, form):
        messages.success(self.request, 'Location updated successfully!')
        return super().form_valid(form)


# Supplier Views
@method_decorator(login_required, name='dispatch')
class SupplierListView(ListView):
    """View for listing suppliers"""
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'


@method_decorator(login_required, name='dispatch')
class SupplierDetailView(DetailView):
    """View for viewing supplier details"""
    model = Supplier
    template_name = 'inventory/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get related data
        context['items'] = Item.objects.filter(supplier=self.object, is_active=True)
        context['purchase_orders'] = PurchaseOrder.objects.filter(supplier=self.object).order_by('-created_at')

        return context


@method_decorator(login_required, name='dispatch')
class SupplierCreateView(CreateView):
    """View for creating new suppliers"""
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('inventory:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, 'Supplier created successfully!')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class SupplierUpdateView(UpdateView):
    """View for updating suppliers"""
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'

    def get_success_url(self):
        return reverse('inventory:supplier_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Supplier updated successfully!')
        return super().form_valid(form)


# Dashboard and Reports
@login_required
def inventory_dashboard(request):
    """View for inventory dashboard with summary statistics"""
    # Get summary statistics
    wisp_item_count = Item.objects.filter(company='wisp', is_active=True).count()
    fno_item_count = Item.objects.filter(company='fno', is_active=True).count()

    wisp_stock_value = Item.objects.filter(
        company='wisp',
        is_active=True
    ).exclude(
        total_value=None
    ).aggregate(total=Sum('total_value'))['total'] or 0

    fno_stock_value = Item.objects.filter(
        company='fno',
        is_active=True
    ).exclude(
        total_value=None
    ).aggregate(total=Sum('total_value'))['total'] or 0

    low_stock_items = Item.objects.filter(
        is_active=True,
        quantity__gt=0,
        quantity__lte=F('minimum_stock')
    )

    out_of_stock_items = Item.objects.filter(
        is_active=True,
        quantity=0
    )

    # Get recent activity
    recent_movements = StockMovement.objects.all().order_by('-movement_date')[:10]
    recent_purchase_orders = PurchaseOrder.objects.filter(
        status__in=['ordered', 'partially_received']
    ).order_by('-order_date')[:5]

    context = {
        'wisp_item_count': wisp_item_count,
        'fno_item_count': fno_item_count,
        'wisp_stock_value': wisp_stock_value,
        'fno_stock_value': fno_stock_value,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'recent_movements': recent_movements,
        'recent_purchase_orders': recent_purchase_orders,
    }

    return render(request, 'inventory/dashboard.html', context)


@login_required
def stock_valuation_report(request):
    """View for stock valuation report"""
    # Group items by category and company
    items_by_category = {}

    # Get categories with items
    categories = Category.objects.filter(items__is_active=True).distinct()

    for category in categories:
        wisp_items = Item.objects.filter(
            category=category,
            company='wisp',
            is_active=True
        ).exclude(total_value=None)

        fno_items = Item.objects.filter(
            category=category,
            company='fno',
            is_active=True
        ).exclude(total_value=None)

        wisp_value = wisp_items.aggregate(total=Sum('total_value'))['total'] or 0
        fno_value = fno_items.aggregate(total=Sum('total_value'))['total'] or 0

        if wisp_value > 0 or fno_value > 0:
            items_by_category[category.name] = {
                'wisp_value': wisp_value,
                'fno_value': fno_value,
                'total_value': wisp_value + fno_value,
                'wisp_count': wisp_items.count(),
                'fno_count': fno_items.count(),
                'total_count': wisp_items.count() + fno_items.count(),
            }

    # Calculate totals
    wisp_total = sum(cat_data['wisp_value'] for cat_data in items_by_category.values())
    fno_total = sum(cat_data['fno_value'] for cat_data in items_by_category.values())

    context = {
        'items_by_category': items_by_category,
        'wisp_total': wisp_total,
        'fno_total': fno_total,
        'grand_total': wisp_total + fno_total,
    }

    return render(request, 'inventory/stock_valuation_report.html', context)


@login_required
def stock_movement_report(request):
    """View for stock movement report"""
    # Filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    company = request.GET.get('company')

    # Set default date range to current month if not provided
    if not start_date:
        start_date = timezone.now().replace(day=1).date()
    else:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = timezone.now().replace(day=1).date()

    if not end_date:
        end_date = (start_date.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)
    else:
        try:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = (start_date.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(
                days=1)

    # Build filter
    movement_filter = Q(movement_date__date__gte=start_date, movement_date__date__lte=end_date)

    if company:
        movement_filter &= Q(item__company=company)

    # Get movement data
    movements = StockMovement.objects.filter(movement_filter)

    # Group by movement type
    movement_summary = movements.values('movement_type').annotate(
        count=Count('id'),
        total_items=Sum(
            Case(
                When(movement_type='in', then=F('quantity')),
                When(movement_type='out', then=Func(F('quantity'), function='ABS')),
                default=F('quantity'),
                output_field=models.PositiveIntegerField()
            )
        )
    )

    # Prepare context
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'company': company,
        'movements': movements.order_by('-movement_date'),
        'movement_summary': movement_summary,
    }

    return render(request, 'inventory/stock_movement_report.html', context)