# Imports
from .base import BasePlatform
from .github import GitHubPlatform
from .bitbucket import BitbucketPlatform
from .friendcode import FriendCodePlatform
from .assembla import AssemblaPlatform
from .gitlab import GitLabPlatform
from .gr_gitlab import GrGitLabPlatform


# Supported platforms
PLATFORMS = (
    # name -> Platform object
    ('gr_gitlab', GrGitLabPlatform()),
    ('github', GitHubPlatform()),
    ('bitbucket', BitbucketPlatform()),
    ('friendcode', FriendCodePlatform()),
    ('assembla', AssemblaPlatform()),
    ('gitlab', GitLabPlatform()),

    # Match url
    ('base', BasePlatform()),
)

PLATFORMS_MAP = dict(PLATFORMS)
