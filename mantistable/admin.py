from django.contrib import admin

from .models import Table, TableData, SparqlEndpoint, ServerState

admin.site.register(Table)
admin.site.register(TableData)
admin.site.register(SparqlEndpoint)
admin.site.register(ServerState)
