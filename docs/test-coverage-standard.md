# 测试覆盖率标准（rainbond-console）

> 状态：covered gate 当前为 **advisory（不阻断合并）**，观察若干 PR 后翻为强制。
> 适用分支：以 `staging/console-optimize` 为集成分支（release train），所有 feature PR 打到它并跑门禁；main 仅最终发版合一次。

## 1. 覆盖率哲学

本仓库采用**两类互补的覆盖率**，不要混淆：

| 类型 | 衡量什么 | 工具 | 门禁 |
|------|---------|------|------|
| **能力/trace 覆盖** | 关键业务能力（capability_id）是否有对应回归测试 | `test-manifest.json` + `scripts/validate_test_manifest.py`（`make test-manifest-check`）、`scripts/report_trace_coverage.py` | unit-test job 内**强制** |
| **行覆盖（本标准）** | 代码行/分支被测试执行的比例 | `pytest-cov` + `diff-cover` | coverage-gate job，当前 **advisory** |

> 为什么不卡**全局行覆盖**：本仓库是"能力定向测试"模型（stub 单测覆盖高频核心路径，大量 region-API 胶水代码不做单测），全局行覆盖天然偏低，卡全局阈值既不公平也无意义。因此**只对 PR 新增/改动的代码**卡覆盖率（diff coverage）。

## 2. 新代码标准（核心规则）

**PR 中新增/改动的代码，diff 行覆盖率 ≥ 80%。**

- 衡量对象：本次 PR 相对 base 分支（`origin/<base>`）的 diff 命中的代码行。
- 阈值：80%（对齐团队全局测试规范的最低 80%）。
- 现状：advisory（`coverage-gate` job 设 `continue-on-error: true`，报告但不阻断）。稳定后删除该行翻为强制。
- 例外：纯删除、配置/文档、确实无法单测的 region-API 透传，可在 PR 说明里注明豁免理由。

## 3. CI 如何执行

`.github/workflows/pr-ci-build.yml` 的 `coverage-gate` job：
1. `actions/checkout` 用 `fetch-depth: 0`（diff-cover 需要 base 历史）。
2. 跑测试并收集覆盖率：`python scripts/run_pytest.py . -- -q --cov=console --cov=www --cov=openapi --cov-append --cov-report=`。
   - 注意：`run_pytest.py` 每个测试文件起独立子进程（隔离手写 stub 测试），靠 `--cov-append` 把各文件覆盖率累加进单个 `.coverage`。
3. `coverage xml -o coverage.xml`。
4. `diff-cover coverage.xml --compare-branch=origin/${GITHUB_BASE_REF} --fail-under=80`。

## 4. 本地自查

```bash
# 在 rbd-console-typecheck:3.11 镜像内（或等价 py3.11 + requirements 环境）
coverage erase
python scripts/run_pytest.py . -- -q --cov=console --cov=www --cov=openapi --cov-append --cov-report=
coverage xml -o coverage.xml
pip install diff-cover   # 一次性
diff-cover coverage.xml --compare-branch=origin/staging/console-optimize --fail-under=80
```

只看自己改的文件覆盖率时，diff-cover 会自动只统计 diff 命中的行。

## 5. 全局行覆盖率基线（仅供参考，非门禁）

> 截至 2026-06-16，全量 `console/tests` 套件对 `console/`+`www/`+`openapi/` 的全局行覆盖率基线：**<待补：基线测量完成后填入>%**。
>
> 该数字仅作趋势参考，**不作为门禁**（原因见 §1）。门禁只卡新代码 diff 覆盖率。

## 6. 翻为强制（blocking）的步骤

观察若干 PR、确认 80% 阈值对正常开发不造成过度摩擦后：
1. 删除 `coverage-gate` job 的 `continue-on-error: true`。
2. 在分支保护里把 `coverage-gate` 加入 required status checks（见分支保护配置）。
