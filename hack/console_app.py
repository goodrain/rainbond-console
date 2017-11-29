from gunicorn.app.wsgiapp import WSGIApplication
from goodrain_web.wsgi import application

class GunicornWSGI(WSGIApplication):

    def init(self, parser, opts, args):
        args = ['goodrain_web.wsgi']
        super(GunicornWSGI, self).init(parser, opts, args)

    def load_wsgiapp(self):
        self.chdir()
        return application


if __name__ == '__main__':
    GunicornWSGI("%(prog)s [OPTIONS] [APP_MODULE]").run()

