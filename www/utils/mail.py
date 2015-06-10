from django.core.mail import send_mail

import sys
reload(sys)
sys.setdefaultencoding('UTF-8')

class MailUtil(object):
            
    def get_inviteContent(self, link_url):
        return "rest"
#         content = u"尊敬的用户您好，"
#         content = content + "<br/>"
#         content = content + u"非常感谢您申请试用 好雨云平台！ 请点击下面的链接完成注册:"
#         content = content + "<br/>"
#         content = content + u"注册链接: <a target='_blank' href=" + link_url + ">注册好友云平台</a>"
#         content = content + "<br/>"
#         content = content + u"我们的服务在一定的资源范围内永久免费！内测阶段也可以申请增加免费资源，增加的资源在产品正式版上线后也不会另收费用哦！另外参与内测并提交问题报告的用户，正式上线后还会有更多的福利。"
#         content = content + "<br/>"
#         content = content + u"我们的文档及博客正在建设中，以后会陆续发布一系列好雨云平台的使用教程和技巧，欢迎关注！"
#         content = content + "<br/>"
#         content = content + u"您在使用过程中遇到的任何问题，或者对平台有任何建议，都可以通过以下途径提交反馈。对于提出高质量的反馈的用户，还有精美礼品等待您！"
#         content = content + "<br/>"
#         content = content + "Email： ares@goodrain.com"
#         content = content + "<br/>"
#         content = content + u"微信公众号：goodrain-cloud "
#         content = content + "<br/>"
#         content = content + u"联系电话：13621236261"
#         content = content + "<br/>"
#         content = content + u"再次感谢您关注我们的产品！"
#         content = content + "<br/>"
#         content = content + u"好雨科技 (Goodrain Inc.) CEO 刘凡"
        
    def send_invite_mail(to, content):
        send_mail("invite user", content, 'no-reply@goodrain.com', [to])
        
    def send_invite_mail_withHtml(to, html_content):
        send_mail('test', "", 'no-reply@goodrain.com', [to], fail_silently=False, auth_user=None, auth_password=None, connection=None, html_message=html_content)
    
