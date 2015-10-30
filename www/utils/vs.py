from distutils.version import LooseVersion


class AppVersion(LooseVersion):

    def __add__(self, value):
        last_v = self.version[-1]
        last_v += int(value)
        self.version[-1] = last_v

    def __str__(self):
        return '.'.join([str(e) for e in self.version])


def increase_version(version, increase):
    v = AppVersion(version)
    v + increase
    return v.__str__()
