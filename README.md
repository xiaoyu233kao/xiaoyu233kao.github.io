# 烤鱼日常

基于 Hexo 7 与定制 Edinburgh 主题的个人摄影日志与随笔站点，发布于 GitHub Pages：https://xiaoyu233kao.github.io/ 。

## 内容结构

- **旅行**（首页 `/`）：位于 `source/_posts/`，使用 `旅行` 分类，配合本地图片或图床 `xiaoyu233kao/picgo-bed` 展示。
- **画廊**（`/gallery/`）：由 `source/gallery/index.md` 配置照片数量与图床前缀，尺寸占位信息维护在 `source/_data/gallery_dimensions.json`。
- **随笔**（`/essays/`）：公开随笔位于 `source/_posts/`（使用 `layout: essay` 与 `随笔` 分类）；仅作者可见的私人随笔保存在本地 `私人随笔/`（由 `.gitignore` 排除，仅同步至私有备份仓库），公开列表与归档通过 `source/_data/private_essays.yml` 仅保留标题、日期与私有链接。
- **关于 / 归档**（`/about/`、`/archives/`）：关于正文位于 `source/about/index.md`；归档通过 `scripts/private-essay-archives.js` 合并私有随笔外链。

## 本地预览与构建

```powershell
# 推荐（与 GitHub Actions 一致，需启用 pnpm / corepack）
pnpm install --frozen-lockfile
pnpm server
pnpm build

# Windows PowerShell 受执行策略限制或未安装全局 pnpm 时
npm.cmd run server
npm.cmd run build
```

`npm run build` / `pnpm build` 会先清理 `public` 再重新生成，并由 `scripts/private-content-guard.js` 阻止私人内容进入公开输出。

## 发布与维护

- 推送到 `main` 分支后，由 `.github/workflows/pages.yml` 自动构建并部署到 GitHub Pages（仅维护文档更新时可在提交信息中使用 `[skip ci]` 跳过构建）。
- 工程维护约定见 [AGENTS.md](AGENTS.md)，历次变更与检查记录见 [工作日志.md](工作日志.md)，私有快照与恢复说明见 [备份说明.md](备份说明.md)。
