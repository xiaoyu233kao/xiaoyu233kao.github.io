# 沿途拾光｜个人摄影博客模板

一个无需构建工具、可直接部署到 GitHub Pages 的静态摄影日志模板。

## 本地预览

直接打开 `index.html`，或在此目录运行：

```powershell
python -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 替换内容

- 网站名称：搜索并替换“沿途拾光”
- 个人资料：修改 `about.html`
- 首页文章：复制或修改 `index.html` 中的 `<article class="entry">`
- 文章正文：复制 `post.html`，并修改标题、日期、文字和图片
- 照片：建议创建 `images/` 文件夹，把图片地址换成 `images/你的照片.jpg`

## 发布到 GitHub Pages

1. 在 GitHub 新建公开仓库，例如 `photo-journal`。
2. 将本目录的文件上传到仓库根目录并提交。
3. 打开仓库的 **Settings → Pages**。
4. 在 **Build and deployment** 中选择 **Deploy from a branch**。
5. 分支选择 `main`，目录选择 `/ (root)`，保存。
6. 网站地址通常为 `https://你的用户名.github.io/photo-journal/`。

若希望地址直接是 `https://你的用户名.github.io/`，仓库名必须是 `你的用户名.github.io`。

> 示例图片来自 Unsplash，仅用于模板预览。正式发布前请替换为自己的照片。
