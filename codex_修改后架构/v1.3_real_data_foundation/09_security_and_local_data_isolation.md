# 09 · Security 与本地数据隔离

## 1. 目标

数据底座会接触 provider token、本地数据文件和可能受 license 限制的 provider payload。Phase 1A 在写任何真实 provider 输出前,必须先保护本地路径和密钥。

## 2. Git ignore baseline

Phase 1A 实施前应确保以下路径被 gitignore 或等价 guard 保护:

```text
data_lake/
config/data/local/
.env
.env.local
.env.*.local
!.env.example
```

当前仓库已忽略 `runtime/`、`results/`、`data_real/`、`config/live/local/`。v1.3 需要补充 data foundation 专用路径。

## 3. Secrets 配置

允许:

- environment variables。
- local ignored config under `config/data/local/`。
- `.env.local` 等本地文件。

禁止:

- provider token in git。
- token in manifest。
- token in raw payload。
- token in quality report。
- token in test fixture。
- token in terminal examples。
- real account identifier in docs or fixtures。

## 4. Safe example config

可以提交:

```text
config/data/providers.example.yaml
.env.example
```

Example file 只能包含 placeholder:

```yaml
tushare:
  token_env: TUSHARE_TOKEN
  timeout_seconds: 30
```

不能包含看似真实的 token、账号、手机号、邮箱或本地绝对私密路径。

## 5. Logging redaction

日志层必须脱敏:

- token。
- auth header。
- cookie。
- API key。
- account id。
- local credential file path when sensitive。

Redaction 应在 provider metadata 写入前执行,不能只依赖外层日志配置。

## 6. Raw payload quarantine

若发现 raw payload 或 report 包含 secret-like value:

1. 停止 pipeline。
2. 标记 `secret_leak_detected`。
3. 不发布 curated snapshot。
4. 将 artifact 移入 quarantine 或删除未提交本地文件。
5. 记录 incident note。
6. 更换 token 后重新运行。

该流程不涉及 git commit。如果 secret 已进入 git history,必须作为安全事故单独处理。

## 7. License and redistribution

Manifest 必须包含:

- usage_scope: `research_only | unknown | contracted`。
- source_license_note。
- redistribution_allowed: false。

默认不允许 redistribution。Provider payload 不应进入公共研究报告或提交到 git。

## 8. 本地备份

Data lake 是本地研究资产,但不是源代码:

- 不提交 git。
- 可用外部硬盘或私有备份。
- 备份时保留 manifest 和 hashes。
- 恢复后先运行 hash verification。

## 9. Security acceptance

Phase 1A security acceptance:

- `.gitignore` 包含 v1.3 data and secret paths。
- Example config safe to commit。
- Provider logs redact secrets。
- Manifest request params do not include tokens。
- Tests cover token redaction on metadata/report。
- No real provider output under tracked paths。

