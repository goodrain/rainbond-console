# mypy P5 (views/openapi) — 进度与恢复锚点

> 分支 `chore/mypy-p5-views`（base = goodrain:staging/console-optimize，head = yangkaa）。
> openapi 走单独 PR（分支 `chore/mypy-p5-openapi`，P5 views 之后做）。
> 约定/坑全在 [[2026-06-14-mypy-autonomous-progress]] + [[mypy-typecheck-harness]] + [[mypy-stub-tests-gate]]。

## 核心约定（V0 确立）
view 上下文属性（self.user/tenant/team/region/app/enterprise）在 base 类按运行时契约标成
**非 Optional 具体类型**（class-level 注解），`__init__` 里每个 `= None` 加单处
`# type: ignore[assignment]`。字符串链式赋值属性同理钉成 str。这样子类 view 体内 self.attr 干净。
- self.user → www.models.main.Users；enterprise → TenantEnterprise；tenant/team → Tenants；
  region → console.models.main.RegionConfig；app → ServiceGroup；region_name/response_region/
  tenant_name/team_name → str；perm_app_id/app_id/app_upgrade_record → Any（遗留多态）。
- 遗留不一致（Users.user_id int-as-str、enterprise_id 可空、regionapi Optional data、
  DRF 异常 handler 防御式 getattr）→ type:ignore + NOTE，不改行为。
- 级联：view 是叶子，但少数已 whitelist 模块 import view：operation_log→app_config.base.AppBaseView；
  services/app.py→app_create/source_outer.check_endpoints；openapi apps.py→app_config.app_volume。
  每批标完跑全目录 gate，确认 whitelist 全 0。

## 验证三连（每批必跑）
1. 单模块 strict：`docker run --rm -v "$(pwd)":/app -w /app -e PIP_SRC=/tmp/pip-src --tmpfs /tmp:size=512m rbd-console-typecheck:3.11 mypy --config-file mypy.ini --no-incremental --cache-dir=/tmp/mc --disallow-untyped-defs --check-untyped-defs -m <模块>`（逐个字面量列 -m）
2. 全目录 gate（磁盘缓存）：`docker run --rm -v "$(pwd)":/app -w /app --tmpfs /tmp:size=512m rbd-console-typecheck:3.11 mypy --config-file mypy.ini --cache-dir=/app/.mypy_cache console/ www/ openapi/`，grep 确认 whitelist 模块全 0
3. unit-test：`docker run ... python scripts/run_pytest.py console/tests -- -q` 0 失败

## 批次进度（console/views，PR #1）
- [x] **V0**：base.py + app/ + platform_resources/ —— commit 4d6a6f9d9，pushed。base.py 立约定；
  operation_log:412 级联 union-attr→arg-type。strict 0 / 全目录 whitelist 0 / unit-test 0 失败。
- [x] **V1**：app_config/ 子包（16 文件）—— commit 0335dfbe4，pushed。base.py 我标（service:TenantServiceInfo，
  app/component:Any 避免 operation_log 级联）；其余 14 文件 Sonnet agent 标，AST 校验确认零逻辑改动（仅注解+import），
  strict 0 / 全目录 whitelist 0 / unit-test 0 失败。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：
    - app_plugin.py:177,188 `logger.exception(e)` 引用已被 except 块删除的 e → NameError（该错误路径执行时）。
    - app_domain.py:230 `Response(400, "no param...", ...)` 字符串当第2位置参 status → 状态码畸形。
    - app_domain.py:992-1000 `bind_domain` 缺必填 rule_extensions 位置参 + 传 None 给 str；`unbind_domain` 只返回 None 却解包 (code,msg) → TypeError。
- [x] **V2**：app_create/ 子包（10 文件 + __init__）—— commit a30a792fc，pushed。Sonnet agent 标（API error 中断在收尾报告，
  但 10 文件 edit 已完成）；AST 校验零逻辑改动，strict 0 / 全目录 whitelist 0（含 services/app.py:607 cross-edge 仍 0）/ unit-test 0 失败。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：
    - source_code.py: `import_tar_images` RegionInvokeApi 上不存在 → AttributeError；put() 有路径不 return（缺 return）；某 handler 返回 (int,str) 元组而非 Response。
    - docker_compose.py: `savepoint_commit(None)`（sid 恒 None，savepoint 从未创建）latent bug。
    - 多处 get_*（group/compose/oauth/upload record）返回 None 未防护后解引用；py2 Exception.message。
- [x] **V3**：center_pool/(6) + plugin/(8) 子包（14 文件）—— commit 9f5d36409，pushed。Sonnet agent 标；AST 校验
  仅 app_export.py 有声明的变量重命名（app_version→app_version_obj，循环体内，行为等价已人工核对），余 13 文件零逻辑改动；
  strict 0 / 全目录 whitelist 0 / unit-test 0 失败。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：
    - app_import.py CenterAppTarballDirView：继承 JWTAuthApiView 却用 self.tenant/self.response_region（只在 RegionTenantHeaderView 有）→ AttributeError；delete_import_app_dir 返回 None 却 .to_dict()。
    - plugin_config.py ConfigPluginManageView.delete：delete_config_group_by_meta_type 返回 None 却传给 json_config_group。
    - apps.py AppVersionUDView.delete：get_rainbond_app_by_app_id 传 2 参但签名只收 1 参（兄弟方法传 1 参，疑似传错）。
    - plugin_create.py PluginCreateView except：tenant_plugin 可能 None 未防护用 .plugin_id。
- [x] **V4**：team/enterprise/app_manage/app_overview（4 大文件 ~4400 LOC）—— commit 6033397e8，pushed。Sonnet agent 标；
  AST 校验：enterprise.py 仅 2 处 keyword-arg 重排（new_information/old_information 移到 enterprise_id 前，kwarg 顺序无关行为等价），余 3 文件零逻辑改动；
  strict 0 / 全目录 whitelist 0 / unit-test 0 失败。enterprise.py:1065 EnterpriseRegionLangVersion 重复定义 type:ignore[no-redef]。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：
    - team.py:159 msg_show 中文串内含 ASCII "-" → `"x" - "y"` TypeError（该 raise 路径）；:507 team.region（Tenants 无 region 属性）；:693 self.response_region.region_name（response_region 是 str）；:906 user_repo.get_user_by_enterprise_id 不存在；:1228 create_registry_auth 缺 hub_type/user_id 必填参。
    - enterprise.py:506 update_long_version 缺 show/first_choice 必填参；:672 status.HTTP_404_NOTFOUND 拼写错（应 HTTP_404_NOT_FOUND）。
    - app_overview.py:882 check_service_cname 参数疑似错位（service_region 当 name、None 当 region）。
- [x] **V5**：service_share/user_operation/oauth/webhook/public_areas/mcp_query/adaptor（7 文件 ~5000 LOC）—— commit ccccd07d9，pushed。
  Sonnet agent 标；AST 校验仅 public_areas.py 1 处变量重命名（data→region_app_obj，循环体内 RegionApp，已核对等价），余 6 文件零逻辑改动；
  flake8 0 E501（按字符数；先前 awk 按字节误报）；strict 0 / 全目录 whitelist 0 / unit-test 0 失败。mcp_query MCPQueryRPCMixin 3 处 type:ignore[misc]。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：
    - user_operation.py:578 UserFavoriteUDView.delete 引用未定义 `favorite` → NameError；:234 SendResetEmail.post 某路径不 return。
    - public_areas.py:573 / service_share.py:268 handler 某路径不 return（返回 None）。
- [x] **V6**（合并原 V6+V7）：剩余全部 top-level 文件（~60 个）—— commit 94f3ab4ec，pushed。3 个并行 Sonnet agent；
  AST 校验仅 3 处声明的变量重命名（group.py component_names→component_names_text、registry.py result→registry_auths、
  app_monitor.py result→service_resource，均已人工核对等价），余全部零逻辑改动；加 `[mypy-console.views.*]` 通配收口；
  清掉 3 个 agent 引入的未用 typing import（storage_statistics/operation_log/groupapp_migration）。
  **整个 console.views 包 strict-clean**；全目录 whitelist 0 / unit-test 0 失败。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：user_accesstoken.py:77 access_key 未定义→NameError；
    services_toplogical.py:46/118 get_no_group_service_status_by_group_id 缺 team_id/enterprise_id 参；
    rbd_plugin.py:84 region_services 未 import→NameError；:88 list_plugins 返回元组被当 list 迭代；
    app_config_group.py:91 delete_config_group 返回 None 却下标；enterprise_active.py:107 base64.decodestring(py3.9 移除)；
    region.py:262 get_user_perm_role_in_permtenant 方法不存在。
- **PR #1（views）完成**：V0-V6 共 7 commit。flake8：type:ignore+NOTE 长行有 E501（与已合并的 P4 同模式；flake8 非 required check）。
  待创建 PR base=goodrain:staging/console-optimize head=yangkaa:chore/mypy-p5-views。
- 注意：mcp_query.py MCPQueryRPCMixin 多继承不兼容已 type:ignore[misc]（V5 处理）。

## 批次进度（openapi，分支 chore/mypy-p5-openapi，PR #1974）—— 完成 ✅
- 分支基于干净 upstream/staging/console-optimize（不含 views 改动，两 PR 独立）。
- openapi/views/base.py 我标（BaseOpenAPIView→TeamNoRegion→TeamAPI→TeamApp→TeamAppService 整条链上下文属性：
  enterprise:TenantEnterprise/user:Users/team:Tenants/region:RegionConfig/region_name:str/app:Any/service:TenantServiceInfo；
  request.user 是 User|AnonymousUser → 所有 request.user.X 用 type:ignore[union-attr]）。
- 其余 55 文件 3 个并行 Sonnet agent（含 DRF serializer：validate/create/to_representation/method field；auth；models；v2）。
- **越权拦截**：2 个 agent 给原本无 *args/**kwargs 的 handler 加了 *args/**kwargs（v2/auth/views.py、v2/views/enterprise_view.py 共 6 处），AST 校验抓到，已全部回退为原签名。
  4 处声明的变量重命名（gateway/mcp.views/region_view×2，serializer/data 同名复用，已核对）。清掉 4 个未用 typing import。
- 全 strict 0 / 全目录 whitelist+openapi 0 / unit-test 0 失败。commit d3c1807e1，pushed。
  - 抓出 latent bug（type:ignore 保留，待 fix PR）：
    - apps.py: team_repo 未定义(:1321)；deploy_repo 在 module 上调单例方法(:379)；batch_action 返回3值只解包2；delete_import_app_dir 返回None 却.to_dict()；self.tenant 用在只设 self.team 的类；HelmChart/ResourceOverview 重复定义；HelmChart.post 缺 return；GroupService 缺多个方法(recover_app 等)。
    - enterprise_view.py: EnterpriseServices 缺 get_app_ranking/get_monitor_message 等多方法；service_overview 未定义(NameError)；ResourceOverview 重复定义。
    - team_view.py:230 except PermRelTenant(模型非异常)；:396 delete_team_region 返回None 解包；appstore_view.py:70 except TenantEnterpriseToken(模型)。
    - 多处 serializers.ValidationError("msg", status_int) 把 HTTP 状态码当 code(str) 传（不生效）。
    - user_view.py enterprise_center_user_id / app_serializer.py:246 validators.ValidationError(不存在) → AttributeError。

## ⚠️ 复用方法：AST 越权校验（本次新增，很有效）
派 agent 批量标注后，提交前用脚本对每个改动文件比对"剥掉注解+import 后的 AST"（HEAD vs 工作树）：
相同=纯注解零逻辑改动；DIFF=有逻辑改动需人工核对。本次靠它抓到 agent 偷加 *args/**kwargs（v2 两文件）+ 确认所有
变量重命名是声明过的。脚本见 /tmp/ast_check2.py（StripAnn transformer：清 FunctionDef.returns/arg.annotation、
AnnAssign(有值)→Assign/(无值)→删、删 Import/ImportFrom）。

## P5 全部完成并已合并 ✅
- PR #1972 (console.views) → squash 合并 commit 3061d8eda；PR #1974 (openapi) → squash 合并 commit b9ecb46e4。
  均已落 staging/console-optimize。合 #1972 后 #1974 的 mypy.ini 末尾段冲突已 rebase 解决（views+openapi 两组段都保留）。
  coverage-gate（advisory diff-cover ≥80%，非 required）对 type-only PR 必红，已确认不阻塞、直接合。required 4 项全绿。
- 下一步（用户计划）：合 PR 后做 M2 regionapi 响应 TypedDict（基于 [[2026-06-13-m2-regionapi-domain-breakdown]] + [[2026-06-13-m2-go-response-structs]]），单独 PR。
