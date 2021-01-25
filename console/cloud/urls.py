from console.cloud.views import ProxyView
from django.conf.urls import url

urlpatterns = [url(r"^proxy/(?P<path>.*)", ProxyView.as_view())]
