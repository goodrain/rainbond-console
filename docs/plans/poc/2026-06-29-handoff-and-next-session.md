# 开源应用转模版 — Day1–3 收尾手册 & 新会话提示词（2026-06-29）

> 仓库：rainbond-console，分支 `feat/app-to-template`（本地集成分支，已含 4 个 PR 代码 + 今天 3 个新 fix）
> 集群 `rainbond`（北京/amd64），团队 `tynwrm27`，enterprise_id `5ae43b0db81042d0ba8005386022d1c5`

## 一、今天完成了什么（已验证）

| 阶段 | 结果 |
|------|------|
| Day1 从零重建 Dify | 9/9 running，0 人工介入（co-tenant DNS 冲突自动加 `-tpl` 后缀恢复） |
| Day2 净化 + 本地一键装 | 3178：9/9 + 密钥随机一致 + 同源 nginx 200 + host 自动重映射 |
| Day3 发布企业市场 | store_app `05df84f525ce41c2ac62958cdc116387` v1.14.2（上游镜像、含首次使用指南） |
| Day3 升级 modify-not-add | 预览：9/9 type:upgrade、0 add、None:group 密钥不被覆盖 |
| Day3 市场 None:group 解析 | 重装后 db-postgres/plugin-daemon 密钥都解析为随机一致值（fcc1e594…） |

## 二、发现并修复的 3 个 console bug（已 commit，未 push）

本地分支 `feat/app-to-template` 顶部 3 个 commit，工作树干净，**均已热同步到 hs 生效 + 带单测**：

| commit | 内容 | 归属 PR |
|--------|------|---------|
| `91aec5407` | `_apply_share_overrides` 字段合并保 env `name`（否则装快照崩 `1048 Column 'name' cannot be null`） | #2018 |
| `a98d4d2b0` | 升级路径重新应用 #2017 hostname remap（`AppUpgrade.__init__` 加 `_build_install_remap`/`_apply_install_remap_to_template`） | #2017 |
| `9fb19cbb9` | 云/市场装解析 `**None:group**`（`utils.resolve_none_placeholders` + `install_service`/`install_service_when_upgrade_app` 调用 + `__save_env` int 守卫） | #2014 / install_service |

测试文件：`test_share_overrides.py`、`test_upgrade_hostname_remap.py`、`test_none_group_resolve.py`、`test_hostname_remap.py`（全绿）。

## 三、待合并 PR（upstream goodrain/rainbond-console，全部 OPEN）

| PR | 标题 | head 分支(yangkaa:) |
|----|------|---------------------|
| #2014 | feat: support **None:group** env parameterization for template install | feat/none-group-env-param |
| #2016 | feat(mcp): add closed-loop signal tools for troubleshoot loop | feat/m1-closed-loop-mcp-tools |
| #2017 | feat: snapshot image rewrite, app-store publish, and install hostname remap | feat/template-publish-and-hostname-remap |
| #2018 | fix: merge share_service_list env overrides instead of replacing full template | fix/share-service-list-merge |

> 注：4 个 PR 的代码都已在 `feat/app-to-template` 集成分支里；今天 3 个新 fix 也在这里但**未 push、未开 PR**。

## 四、核心架构结论

- **本地装路径** `NewComponents`：有 #2014（None:group 解析）+ #2017（hostname remap）两个安装期改写。
- **云/市场装路径** `install_service` / `__save_component_meta`：两者**原本都缺**。今天补了 #2014（None:group），**#2017 host-remap 在云路径仍缺**。
- 影响面：真实用户装进**独立 namespace**（无碰撞）两条路径都 OK；**同租户重装/市场装**（策展、测试）才暴露缺口。

## 五、待办（按优先级）

1. **【代码】云/市场装补 #2017 host-remap**（第 4 个同类修复，机械、镜像前 3 个套路）：在 `install_service`/`install_service_when_upgrade_app` 保存组件前，对 inner-env host 值 + config-file 内容做 install-time remap（installed k8s_service_name），参考 `NewComponents._collect_hostname_remap`/`_apply_hostname_remap` 与 commit a98d4d2b0。修完同租户市场装即可全绿 → 拿到「市场一键安装可用」铁证。
2. **【验证】** 修完后清掉坏的 3182、重装企业市场 → 确认 9/9 + nginx 200 + 密钥随机一致 + host 指向自己的库；或借一个干净团队装一遍（真实用户路径）。
3. **【代码】postgres/weaviate 持久化**（M0 parity 缺口）：源 app 3174 给 db-postgres 挂 `/var/lib/postgresql/data`（PGDATA 已是子目录，就绪）、weaviate 挂 `/var/lib/weaviate`，选 RWO/block 卷类型（postgres 不要 RWX/NFS）。否则重启丢数据，且当前 3182 的 plugin-daemon 28P01 部分也与无持久化+同租户连错库叠加。
4. **【收口】** 把 3 个新 commit 分发到对应 PR 分支 push（或单开 PR）；推进 4 个旧 PR 合并。
5. **【清理】** 删 co-tenant 测试产物 3182（坏）；按需保留 3178（升级目标）。
6. **【可选】** 真集群 E2E / Harbor 泛化复跑同流程。

## 六、关键资产与 ID

- 源 app **3174** `dify-template-src`（go-forward 发布源；worker 现配 1536；入口 `http://gr920016-80-tynwrm27.dev.goodrain.com`）
- 本地装 v1 **3178**（健康 9/9，升级测试目标）
- 市场装 **3182**（plugin-daemon 28P01 + api/worker PVC unbound，co-tenant 坏，可删）
- 快照：**515** `1.14.2-safe2`（已发布）、**516** `1.14.3`（升级用）、513 废弃
- hidden template app_model `4cc2627a1da2a7a4e39e8559703de032`，upgrade_group_id `2867`
- 企业市场 store_app **05df84f525ce41c2ac62958cdc116387** v1.14.2；market_id 263「好雨科技企业服务商店」(domain=enterprise)；market_id 4 开源公共市场
- M0 旧源 3141（closed，保留勿删）；Harbor 3159

## 七、运维/排障要诀

- **热同步 console 改动**：`DEPLOY_ENV=hs bash ~/code/rainbond-e2e-tests/scripts/sync-console.sh --env hs --file <相对路径>`；gunicorn `--reload` 多 worker 有重载竞态 → 改完立刻调用可能命中旧 worker，用 `ssh hs "kubectl -n rbd-system exec rbd-app-ui-686c7b7469-jb9fr -c rbd-app-ui -- sh -c 'kill -HUP 1'"` 强制全 worker 重载（`kill` 是 sh 内建，不能直接 `-- kill`）。
- **看 console 异常堆栈**：`ssh hs`，日志在 rbd-app-ui 容器 `/app/logs/goodrain.log`（被吞的异常如 `1048`/`int startswith` 都在这抓到）。
- **跑单测**：`orb start` 起 OrbStack，再 `docker run --rm -v "$(pwd)":/app -w /app -e PIP_SRC=/tmp/pip-src rbd-console-test:py311 python scripts/run_pytest.py <files> -- -q`。
- **删 app**：MCP `rainbond_delete_app` 先空调用拿 confirmation_token，再带 confirm=true + token。
- **市场装**：`install_app_by_market` 只 build 不 start，需再 `operate_app(start)`；同租户装会 co-tenant 后缀。

---

## 八、下次直接粘贴的新会话提示词

```
继续「开源应用转 Rainbond 模版」项目。工作目录 ~/code/rainbond-console，分支 feat/app-to-template。
先读 docs/plans/poc/2026-06-29-handoff-and-next-session.md（完整状态/资产/待办/运维要诀）和记忆
opensource-app-to-template-initiative。

背景一句话：Day1–3 已跑通 从零重建→净化→本地一键装→发布企业市场→升级 modify-not-add，
并发现修复 3 个 console bug（91aec5407/a98d4d2b0/9fb19cbb9，已 commit 在 feat/app-to-template，
未 push）。本地装路径(NewComponents)有 #2014+#2017 两个安装期改写，云/市场装路径(install_service)
今天补了 #2014(None:group)，#2017 host-remap 仍缺。

本次优先做（按需确认）：
1) 给云/市场装路径(install_service / install_service_when_upgrade_app)补 #2017 hostname remap
   （镜像 commit a98d4d2b0 的套路：保存组件前对 inner-env host + config-file 按 installed
   k8s_service_name 重映射），加单测，热同步 hs（注意 HUP 强制重载），删坏的 3182 重装企业市场
   验证 9/9 + nginx 200 + 密钥随机一致 + host 指向自己的库。
2) 源 app 3174 给 postgres/weaviate 加持久化卷（RWO/block，非 RWX），重出快照。
3) 把 3 个新 commit 分发到对应 PR 分支 -push（91aec5407→#2018 / a98d4d2b0→#2017 /
   9fb19cbb9→#2014），推进 #2014/#2016/#2017/#2018 合并。

关键 ID：源 3174、本地装 3178、坏的市场装 3182、快照 515(已发布)/516、app_model 4cc2627a、
upgrade_group_id 2867、企业市场 store_app 05df84f5 / market_id 263、M0 旧源 3141(保留勿删)。
集群 rainbond，团队 tynwrm27，enterprise_id 5ae43b0db81042d0ba8005386022d1c5。
运维：热同步 sync-console.sh --env hs；堆栈在 hs 容器 /app/logs/goodrain.log；单测 orb start + docker rbd-console-test:py311。
```
