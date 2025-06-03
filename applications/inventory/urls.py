# inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.inventory_dashboard, name='dashboard'),

    # Items
    path('items/', views.ItemListView.as_view(), name='item_list'),
    path('items/create/', views.ItemCreateView.as_view(), name='item_create'),
    path('items/<int:pk>/', views.ItemDetailView.as_view(), name='item_detail'),
    path('items/<int:pk>/edit/', views.ItemUpdateView.as_view(), name='item_update'),
    path('items/<int:pk>/add-attachment/', views.add_item_attachment, name='add_item_attachment'),

    # Stock Movements
    path('movements/', views.StockMovementListView.as_view(), name='movement_list'),
    path('movements/create/', views.StockMovementCreateView.as_view(), name='movement_create'),

    # Stock Adjustments
    path('adjustments/', views.StockAdjustmentListView.as_view(), name='adjustment_list'),
    path('adjustments/create/', views.StockAdjustmentCreateView.as_view(), name='adjustment_create'),

    # Purchase Orders
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/create/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/edit/', views.PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    path('purchase-orders/<int:pk>/add-item/', views.add_purchase_order_item, name='add_purchase_order_item'),
    path('purchase-orders/items/<int:pk>/remove/', views.remove_purchase_order_item, name='remove_purchase_order_item'),
    path('purchase-orders/<int:pk>/approve/', views.approve_purchase_order, name='approve_purchase_order'),
    path('purchase-orders/<int:pk>/mark-as-ordered/', views.mark_as_ordered, name='mark_as_ordered'),
    path('purchase-orders/items/<int:pk>/receive/', views.receive_purchase_order_item,
         name='receive_purchase_order_item'),

    # Inventory Counts
    path('counts/', views.InventoryCountListView.as_view(), name='count_list'),
    path('counts/create/', views.InventoryCountCreateView.as_view(), name='count_create'),
    path('counts/<int:pk>/', views.InventoryCountDetailView.as_view(), name='count_detail'),
    path('counts/<int:pk>/add-item/', views.add_inventory_count_item, name='add_inventory_count_item'),
    path('counts/items/<int:pk>/update/', views.update_count_item, name='update_count_item'),
    path('counts/<int:pk>/complete/', views.complete_inventory_count, name='complete_inventory_count'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),

    # Locations
    path('locations/', views.LocationListView.as_view(), name='location_list'),
    path('locations/create/', views.LocationCreateView.as_view(), name='location_create'),
    path('locations/<int:pk>/edit/', views.LocationUpdateView.as_view(), name='location_update'),

    # Suppliers
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),

    # Reports
    path('reports/stock-valuation/', views.stock_valuation_report, name='stock_valuation_report'),
    path('reports/stock-movement/', views.stock_movement_report, name='stock_movement_report'),
]
