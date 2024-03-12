"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from data_manager import views as data_manager_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', data_manager_views.index, name='index'),  # 主页设置为 data_manager 的 index 视图
    path('compile_pdf/', data_manager_views.compile_pdf, name='compile_pdf'),
    path('classify_data_item/', data_manager_views.classify_data_item, name='classify_data_item'),
    path('export_all_classified_data/', data_manager_views.export_classified_data, name='export_classified_data'),
    path('api/load-json-from-s3/', data_manager_views.load_json_from_s3, name='load_json_from_s3'),
    path('set_aws_credentials/', data_manager_views.set_aws_credentials, name='set_aws_credentials'),

    # ... 其他可能的 URL
]

