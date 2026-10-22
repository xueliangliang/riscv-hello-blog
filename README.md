# RISC-V 实验笔记

本仓库保存文章源文件和 Hugo 站点模板。文章以 Markdown 编写，生成的静态站点输出到 `public/`。

## 本地预览

```sh
hugo server
```

Hugo 会显示本地预览地址；修改内容后会自动重新构建。

## 手动构建

```sh
hugo version
hugo --minify
```

生成站点位于 `public/`。本仓库当前测试基线是 Hugo `v0.154.5+extended`；没有 GitHub Actions，构建和部署由维护者手动执行。

文章源文件位于 `content/posts/`，页面模板位于 `layouts/`，样式位于 `static/css/site.css`。`public/` 是可随时重建的产物，不提交到 Git。
