from django.conf.urls import url
from console.cloud.views import EnterpriseSubscribe
from console.cloud.views import EnterpriseOrdersRView
from console.cloud.views import EnterpriseOrdersCLView
from console.cloud.views import BankInfoView
from console.cloud.views import ProxyView


urlpatterns = [
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/subscribe$", EnterpriseSubscribe.as_view()),
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/orders$", EnterpriseOrdersCLView.as_view()),
    url(r"^enterprise/(?P<enterprise_id>[\w\-]+)/orders/(?P<order_id>[\w\-]+)$", EnterpriseOrdersRView.as_view()),
    url(r"^proxy/(?P<path>.*)", ProxyView.as_view()),
    url(r"^bank/info$", BankInfoView.as_view()),
]
