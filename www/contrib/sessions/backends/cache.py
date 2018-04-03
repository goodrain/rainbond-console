from django.contrib.sessions.backends.cache import SessionStore as BaseSessionStore

import logging
logger = logging.getLogger('default')


class SessionStore(BaseSessionStore):

    def load(self):
        try:
            logger.debug('session', 'start load key {}'.format(self.cache_key))
            session_data = self._cache.get(self.cache_key, None)
        except Exception, e:
            logger.error('session', 'load key {} error.'.format(self.cache_key))
            logger.exception('session', e)
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            session_data = None
        if session_data is not None:
            logger.debug('session', 'got data for key {}: {}'.format(self.cache_key, session_data))
            return session_data
        self.create()
        return {}
