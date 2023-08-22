from www.models.main import HelmRepoInfo


class HelmRepo(object):
    def create_helm_repo(self, **params):
        return HelmRepoInfo.objects.create(**params)

    def delete_helm_repo(self, repo_name):
        perms = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not perms:
            return None
        return perms.delete()

    def get_helm_repo_by_name(self, repo_name):
        perms = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not perms:
            return None
        return perms[0].to_dict()

    def get_helm_repo_by_url(self, url):
        perms = HelmRepoInfo.objects.filter(repo_url=url)
        if not perms:
            return None
        return perms[0].to_dict()

    def update_helm_repo(self, repo_name, repo_url):
        perms = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not perms:
            return None
        perms[0].repo_url = repo_url
        perms[0].save()


helm_repo = HelmRepo()
