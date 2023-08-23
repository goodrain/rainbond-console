from www.models.main import HelmRepoInfo


class HelmRepo(object):
    def create_helm_repo(self, **params):
        return HelmRepoInfo.objects.create(**params)

    def delete_helm_repo(self, repo_name):
        data = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not data:
            return None
        return data.delete()

    def get_helm_repo_by_name(self, repo_name):
        data = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not data:
            return None
        return data[0].to_dict()

    def get_helm_repo_by_url(self, url):
        data = HelmRepoInfo.objects.filter(repo_url=url)
        if not data:
            return None
        return data[0].to_dict()

    def update_helm_repo(self, repo_name, repo_url):
        data = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not data:
            return None
        data[0].repo_url = repo_url
        data[0].save()


helm_repo = HelmRepo()
