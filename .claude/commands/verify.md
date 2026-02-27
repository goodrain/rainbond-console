# 代码验证

对 rainbond-console Python 项目执行完整的代码验证。

## 执行以下检查

### 1. 代码格式化
```bash
make format
```
使用 yapf 按照 `style.cfg` 配置格式化代码。

### 2. 代码检查
```bash
make check
```
使用 flake8 检查代码质量（max-line-length 129）。

### 3. 测试（如有相关测试）
```bash
pytest
```

## 如果发现问题

- 格式问题：`make format` 会自动修复，检查 diff 确认变更合理
- flake8 错误：根据错误码修复（常见：E501 行过长、F401 未使用导入、E302 空行不足）
- 忽略 W605 警告（已在 Makefile 中配置忽略）

修复后重新运行所有检查，确保全部通过。
