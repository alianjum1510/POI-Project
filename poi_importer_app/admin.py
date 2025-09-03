from django.contrib import admin

from .models import PoI

@admin.register(PoI)
class PoIAdmin(admin.ModelAdmin):
	"""
	Admin interface configuration for the PoI (Point of Interest) model.
    - Displays the ID, name, external PoI ID, category, and average rating in the list view.
    - Enables exact search by internal ID and external PoI ID.
    - Adds filtering by category in the sidebar.
    """
	list_display = ('id', 'name', 'poi_id', 'category', 'avg_rating')
	search_fields = ('id__exact', 'poi_id__exact')
	list_filter = ('category',)
