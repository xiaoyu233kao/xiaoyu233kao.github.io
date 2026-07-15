# 沿途拾光

基于 Hexo 与 Edinburgh 主题的个人摄影日志，发布于 GitHub Pages。

## 新增摄影日志

```powershell
pnpm hexo new "文章标题"
```

编辑 `source/_posts/` 中生成的 Markdown 文件，将照片放入 `source/images/`，并设置文章头部的 `cover_image`。

## 本地预览

```powershell
pnpm install
pnpm server
```

推送到 `main` 分支后，GitHub Actions 会自动构建并发布网站。
