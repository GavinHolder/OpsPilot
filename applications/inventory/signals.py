from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from threading import Thread
from .models import Item, StockMovement, PurchaseOrder, PurchaseOrderItem, StockAdjustment


def send_email_async(subject, message, from_email, recipient_list):
    """Send email asynchronously in a separate thread"""
    thread = Thread(
        target=send_mail,
        args=(subject, message, from_email, recipient_list),
        kwargs={'fail_silently': False}
    )
    thread.daemon = True  # Thread will close when main thread closes
    thread.start()


@receiver(post_save, sender=Item)
def check_low_stock_notifications(sender, instance, **kwargs):
    """Send notifications when an item falls below minimum stock level"""
    if instance.is_low_stock():
        # Prepare recipients list - could be fetched from settings or user preferences
        # For now, just send to superusers or defined stock managers
        recipients = []
        from django.contrib.auth import get_user_model
        User = get_user_model()
        superusers = User.objects.filter(is_superuser=True)
        recipients.extend([user.email for user in superusers if user.email])

        if recipients:
            # Determine level of urgency
            if instance.quantity == 0:
                subject = f'URGENT: Item Out of Stock - {instance.name}'
                urgency = 'OUT OF STOCK'
            else:
                subject = f'Low Stock Alert - {instance.name}'
                urgency = 'LOW STOCK'

            # Prepare message
            message = f"""
            {urgency}: {instance.name}

            Current Stock: {instance.quantity}
            Minimum Stock: {instance.minimum_stock}
            Location: {instance.location}

            Details:
            Company: {instance.get_company_display()}
            SKU: {instance.sku}
            Category: {instance.category}

            Reorder Information:
            Suggested Reorder Quantity: {instance.reorder_quantity}
            Supplier: {instance.supplier}
            Supplier Part Number: {instance.supplier_part_number}

            Click here to view the item: {settings.SITE_URL}/inventory/items/{instance.pk}/
            """

            # Send email asynchronously
            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipients
            )


@receiver(post_save, sender=StockMovement)
def update_item_on_movement(sender, instance, created, **kwargs):
    """Update item details when a stock movement is recorded"""
    if created:
        item = instance.item

        # Update last ordered or received date if applicable
        if instance.movement_type == 'in':
            item.last_received_date = timezone.now().date()

        # Save unit price for historical reference if provided
        if instance.unit_price:
            # Only update the unit price if it's a stock in movement
            if instance.movement_type == 'in':
                item.unit_price = instance.unit_price

        # Save the item
        item.save()


@receiver(post_save, sender=PurchaseOrder)
def purchase_order_status_change(sender, instance, **kwargs):
    """Handle purchase order status changes"""
    # Get old status (if this is an update)
    try:
        old_instance = PurchaseOrder.objects.get(pk=instance.pk)
        old_status = old_instance.status
    except PurchaseOrder.DoesNotExist:
        old_status = None

    # If status changed, send notifications
    if old_status and old_status != instance.status:
        # Prepare recipients
        recipients = []

        # Always notify the creator
        if instance.created_by and instance.created_by.email:
            recipients.append(instance.created_by.email)

        # If approved, notify relevant parties
        if instance.status == 'approved' and instance.approved_by and instance.approved_by.email:
            recipients.append(instance.approved_by.email)

        if recipients:
            subject = f'Purchase Order #{instance.order_number} - Status Changed to {instance.get_status_display()}'
            message = f"""
            The status of Purchase Order #{instance.order_number} has been changed to {instance.get_status_display()}.

            Order Details:
            Supplier: {instance.supplier}
            Company: {instance.get_company_display()}
            Total: {instance.total}

            Click here to view the purchase order: {settings.SITE_URL}/inventory/purchase-orders/{instance.pk}/
            """

            # Send email asynchronously
            send_email_async(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipients
            )


@receiver(post_save, sender=PurchaseOrderItem)
def purchase_order_item_received(sender, instance, **kwargs):
    """Update item when purchase order items are received"""
    # Check if item was received (by comparing with previous quantity received)
    try:
        old_instance = PurchaseOrderItem.objects.get(pk=instance.pk)
        old_quantity_received = old_instance.quantity_received
    except PurchaseOrderItem.DoesNotExist:
        old_quantity_received = 0

    # If quantity received has increased
    if instance.quantity_received > old_quantity_received:
        # Update item's last ordered date if not already set
        item = instance.item
        if not item.last_ordered_date:
            item.last_ordered_date = instance.purchase_order.order_date

        # Update last received date
        item.last_received_date = timezone.now().date()

        # Save the item
        item.save()


@receiver(post_save, sender=StockAdjustment)
def update_item_on_adjustment(sender, instance, created, **kwargs):
    """Update item details when a stock adjustment is recorded"""
    if created:
        item = instance.item

        # Update last counted date
        item.last_counted_date = timezone.now().date()

        # Save the item
        item.save()