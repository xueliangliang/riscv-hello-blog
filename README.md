# XLL技术笔记

本仓库保存文章源文件和 Hugo 站点模板。文章以 Markdown 编写，生成的静态站点输出到 `public/`。

## 系列与文章标签

站名为“XLL技术笔记”。“RISC-V OS实验笔记”是其中一个系列，现有总览地址 `/series/` 与所有文章地址保持不变。

- 文章 front matter 的 `series_id = "riscv-os"` 指向 `data/series.toml` 中的系列定义。添加其他系列时，配置其名称、总览页面与可选代码仓库，再给相应文章设置系列 ID；普通独立文章可以省略此字段。
- `tags` 保留技术主题。系列标签链接到对应总览；普通主题标签使用 Hugo 的实际 taxonomy 页面，自动汇集文章。首页、归档和详情页共用标签模板，不手工拼接中文标签 URL。
- 首页精选入口由 `hugo.toml` 的 `params.featured` 指定，当前为序篇。最新文章按实际发布时间倒序；系列总览仍按课程顺序阅读。

运行 `npm run test:site` 会实际构建 Hugo，检查品牌、发布时间排序、所有文章的系列/主题链接、评论映射及订阅标题，并在隔离副本中验证第二个系列、独立文章和错误系列 ID。

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

系列路线图和术语索引分别位于 `content/series/_index.md`、`content/terms/_index.md`，并通过站点顶部导航访问。文章源文件位于 `content/posts/`，页面模板位于 `layouts/`，样式位于 `static/css/site.css`。`public/` 是可随时重建的产物，不提交到 Git。

## Mermaid 配图

正文使用 fenced `mermaid` 代码块编写图形，并在图中设置 `accTitle` 和 `accDescr`。图形在发布前由固定版本的 Mermaid CLI 渲染成 SVG，Hugo render hook 将代码块显示为图片，同时保留可展开的源码；读者无需加载 Mermaid JavaScript 或访问第三方 CDN。

SVG 放在 `static/diagrams/`，与文章一起提交。文件名是去除首尾空白后的 Mermaid 源码 SHA-256；已有图片的普通 Hugo 构建不需要 Node 或浏览器。修改或新增图形后执行：

```sh
# Node >=22.13；package-lock.json 固定依赖版本
npm ci
# 若 Puppeteer 没有自动安装浏览器，显式安装：
npx puppeteer browsers install chrome
npm run test:diagrams
npm run diagrams
npm run diagrams:check
hugo --minify
```

已有本地 Chrome 时，可用 `PUPPETEER_EXECUTABLE_PATH` 指定其可执行文件。部分 Ubuntu/AppArmor 或容器环境无法启用 Chrome 沙箱；仅渲染自己审查过的本地文章时，可显式使用 `MERMAID_NO_SANDBOX=1 npm run diagrams`。不要以此方式渲染不可信来源。脚本不会关闭系统安全设置，浏览器路径也不写入仓库。

源码与 SVG 不匹配时，Hugo 会报错而不是静默显示旧图。发布前运行 `npm run diagrams:check`；移动端图形支持横向滚动，也可以点击打开原尺寸 SVG。
