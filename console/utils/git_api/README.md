# Git扩展

### 1. 在rainbond-console/console/utils/oauthutil.py中

- 在**OAuthType**类中注册你要扩展的oauth类型
- 如果获取用户信息的数据结构不符合标准输出，需要将其结构放在**OAUTH_SERVICES**中


### 2. 如需要扩展git仓库可在本目录下新建文件书写对应的类来封装以下接口
```.python

    # 获取用户信息
    def get_user(self):
        pass

    # 获取项目列表
    def get_repos(self, **kwargs):
        pass

    # 搜索项目
    def search_repo(self, full_name_or_id, **kwargs):
        pass

    # 获取项目详情
    def get_repo(self, full_name_or_id, **kwargs):
        pass

    # 获取分支或标签列表
    def get_project_branches_or_tags(self, full_name_or_id, type):
        pass
    
    # 创建webhook
    def creat_hooks(self, host, full_name_or_id, endpoint=''):
        pass

    # 获取拉取代码的url（通过Access Key完成认证）
    def get_git_clone_path(self, oauth_user, git_url):
        pass
```

### 3. 将完成的类注册到本目录下的**git_api.py**这个类中    
