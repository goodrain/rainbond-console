from django.urls import path
from . import views

urlpatterns = [
    # 集群管理
    path('regions', views.McpRegionsView.as_view()),
    
    # 团队管理
    path('teams', views.McpTeamsView.as_view()),
    
    # 应用管理
    path('teams/<str:team_alias>/regions/<str:region_name>/apps', views.McpAppsView.as_view()),
    path('teams/<str:team_alias>/regions/<str:region_name>/apps/create', views.McpAppView.as_view()),
    
    # 组件管理
    path('teams/<str:team_alias>/apps/<int:app_id>/components',
         views.McpComponentsView.as_view()),
    path('teams/<str:team_alias>/apps/<int:app_id>/components/create',
         views.McpComponentView.as_view()),
    path('teams/<str:team_alias>/apps/<int:app_id>/components/<str:component_id>',
         views.McpComponentDetailView.as_view()),

    # 端口管理
    path('teams/<str:team_alias>/apps/<int:app_id>/components/<str:component_id>/ports',
         views.McpComponentPortsView.as_view()),
]
