# from django.contrib.gis import admin
# from .models import Profile, Photo, Group, Match, VerificationCode

# # Register your models here.
# admin.site.register(Profile, admin.OSMGeoAdmin)
# admin.site.register(Photo, admin.OSMGeoAdmin)
# admin.site.register(Match, admin.OSMGeoAdmin)
# admin.site.register(Group, admin.OSMGeoAdmin)
# admin.site.register(VerificationCode, admin.OSMGeoAdmin)

# users/admin.py

from django.contrib import admin
from .models import (
    UmUserInformation,
    UmIndustryLabelLevel1,
    UmIndustryLabelLevel2,
    UmIndustryLabelLevel3,
    UmUserAction,
    UmUserTrade,
    UmUserCommunication,
    UmRegion,
    UmSubregion,
    UmCountry,
    UmState,
    UmLanguage
)

@admin.register(UmUserInformation)
class UmUserInformationAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'user_name', 'position', 'department')
    search_fields = ('user_email', 'user_name')
    list_filter = ('position', 'department')

admin.site.register(UmIndustryLabelLevel1)
admin.site.register(UmIndustryLabelLevel2)
admin.site.register(UmIndustryLabelLevel3)
admin.site.register(UmUserAction)
admin.site.register(UmUserTrade)
admin.site.register(UmUserCommunication)
admin.site.register(UmRegion)
admin.site.register(UmSubregion)
admin.site.register(UmCountry)
admin.site.register(UmState)
admin.site.register(UmLanguage)
