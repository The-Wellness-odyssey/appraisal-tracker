from django.contrib import admin
from django.db.models import Count
from .models import AppraisalFile, VehicleValuation, Tag


class VehicleValuationInline(admin.TabularInline):
    model = VehicleValuation
    extra = 0


@admin.register(AppraisalFile)
class AppraisalFileAdmin(admin.ModelAdmin):
    list_display = ('claim_number', 'vehicle_desc', 'status', 'is_priority', 'date_assigned', 'tag_names')
    list_filter = ('status', 'is_priority', 'tags')
    search_fields = ('claim_number', 'vehicle_desc')
    filter_horizontal = ('tags',)
    date_hierarchy = 'date_assigned'
    inlines = [VehicleValuationInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')

    @admin.display(description='Tags')
    def tag_names(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())


@admin.register(VehicleValuation)
class VehicleValuationAdmin(admin.ModelAdmin):
    list_display = ('appraisal_file', 'market_value', 'diminished_value')
    list_filter = ('appraisal_file__status',)
    search_fields = ('appraisal_file__claim_number', 'negotiation_notes')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'file_count')
    search_fields = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_file_count=Count('appraisal_files'))

    @admin.display(description='Files', ordering='_file_count')
    def file_count(self, obj):
        return obj._file_count
