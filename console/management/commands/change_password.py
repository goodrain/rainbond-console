from console.exception.bcode import ErrUserNotFound
from console.repositories.user_repo import user_repo
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Modifies the password for the specified user'

    def add_arguments(self, parser):
        parser.add_argument('--username', default=None, help="Set username ")
        parser.add_argument('--password', default=None, help="Set new password")

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        if not username or not password:
            raise CommandError('username or password can not be empty')
        try:
            user = user_repo.get_user_by_username(username)
        except ErrUserNotFound:
            raise CommandError('User "{}" does not exist'.format(username))
        user.set_password(password)
        user.save()
        print("change user {} password success".format(user.real_name))
