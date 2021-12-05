from django.contrib import admin
# from import_export.admin import ImportExportModelAdmin
from rangefilter.filters import DateRangeFilter, DateTimeRangeFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.conf.locale.en import formats as en_formats
from django.contrib.auth.models import Group
from django_admin_listfilter_dropdown.filters import DropdownFilter
from django.urls import path
from django.http import HttpResponse

from .models import *
from .views import bulk_button
import csv

en_formats.DATE_FORMAT = 'd-m-Y'
en_formats.DATETIME_FORMAT = 'd-m-Y H:i'

@admin.register(Good)
class GoodAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'weights', 'description', 'group', 'visible', 'active', 'order')
    list_editable = ('visible', 'active', 'order')
    list_filter = ('group', )
    change_list_template = "change_temp.html"

    def weights(self, obj):
        return round(obj.weight, 3)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['model_name'] = 'good'
        return super(GoodAdmin, self).changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import_excel_<str:model_name>/', bulk_button),
        ]
        return my_urls + urls


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'population')
    list_editable = ('population',)


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('region', 'id', 'name', 'market_order', 'is_market')
    list_editable = ('name', 'market_order', 'is_market', )
    list_filter = ('region', )


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    exclude = ('time',)
    list_display = ('region', 'market', 'good', 'price', 'author', 'sunday', 'time')
    list_editable = ('price',)
    list_filter = ('region', ('good__name', DropdownFilter), ('sunday', DropdownFilter))
    search_fields = ('good__name', )
    actions = ["export_as_csv"]
    change_list_template = "change_temp.html"
    
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)
        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        return response


    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['model_name'] = 'price'
        return super(PriceAdmin, self).changelist_view(request, extra_context=extra_context)
    
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import_excel_<str:model_name>/', bulk_button),
        ]
        return my_urls + urls

    # def get_form(self, request, obj=None, **kwargs):
    #     form = super(PriceAdmin, self).get_form(request, obj, **kwargs)
    #     form.base_fields['author'].initial = request.user.id
    #     return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'author':
            # setting the user from the request object
            kwargs['initial'] = request.user.id
            # making the field readonly
            kwargs['disabled'] = True
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # def get_rangefilter_sunday_title(self, request, field_path):
    #     return 'By pricing date'


@admin.register(MarketWeight)
class MarketWeightAdmin(admin.ModelAdmin):
    list_display = ('good', 'region', 'weights')
    list_filter = ('region', )
    change_list_template = "change_temp.html"
    
    def weights(self, obj):
        return round(obj.weight, 3)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['model_name'] = 'market_weight'
        return super(MarketWeightAdmin, self).changelist_view(request, extra_context=extra_context)
    
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import_excel_<str:model_name>/', bulk_button),
        ]
        return my_urls + urls


@admin.register(SetDate)
class SetDateAdmin(admin.ModelAdmin):
    list_display = ('id', 'show_default', 'date')
    list_editable = ('date', 'show_default')
    change_list_template = "add_js.html"


    def has_add_permission(self, request):
        MAX_OBJECTS = 1
        if self.model.objects.count() >= MAX_OBJECTS:
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        sunday = to_sunday()
        extra_context['sunday'] = sunday.strftime('%Y-%m-%d')
        is_default = request.POST.get('form-0-show_default', None)
        if is_default:
            SetDate.objects.update_or_create(id=1, defaults={ 'date':sunday })
        return super(SetDateAdmin, self).changelist_view(request, extra_context=extra_context)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'first_name', 'last_name', 'get_region', 'last_login', 'is_staff')
    list_select_related = ('profile', )

    def get_region(self, instance):
        return instance.profile.region
    get_region.short_description = 'Region'


    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.unregister(Group)
