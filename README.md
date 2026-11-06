# XLL技术笔记

本仓库保存文章源文件、Hugo 模板和写作工作流。文章以 Markdown 编写，发布产物生成到全新的 `build/release-*/site/`。

## 系列与文章标签

站名为“XLL技术笔记”。“RISC-V OS实验笔记”是其中一个系列，现有总览地址 `/series/` 与所有文章地址保持不变。

- 文章 front matter 的 `series_id = "riscv-os"` 指向 `data/series.toml` 中的系列定义。添加其他系列时，配置其名称、总览页面与可选代码仓库，再给相应文章设置系列 ID；普通独立文章可以省略此字段。
- `tags` 保留技术主题。系列标签链接到对应总览；普通主题标签使用 Hugo 的实际 taxonomy 页面，自动汇集文章。首页、归档和详情页共用标签模板，不手工拼接中文标签 URL。
- 同一标签不要混用大小写。若历史文章已有多个写法，应在 `content/tags/<term>/_index.md` 固定其规范标题（例如现有的 `VirtIO`），避免 Hugo 在重建时选出不同显示名、干扰精确字节核验；校验器会拒绝未固定的大小写冲突。
- 首页精选入口由 `hugo.toml` 的 `params.featured` 指定，当前为序篇。最新文章按实际发布时间倒序；系列总览仍按课程顺序阅读。

首页、归档、标签页、RSS 和 sitemap 都由 Hugo 自动生成。系列目录从文章的 `series_id`、`series_order` 和 `series_confirmed` 生成，不再手工添加文章链接和勾选；`data/series.toml` 只维护课程分组与尚未发布的计划标题。

## 添加一篇文章

需要 Python 3.11+ 和 Hugo；这些脚本只使用 Python 标准库。创建下一课草稿：

```sh
npm run post:new -- board-port-contract \
  --title "选板先看启动条件：制定一份移植合同" \
  --description "明确真实板卡的启动、内存和外设合同。" \
  --series riscv-os --order 16 --tags RISC-V 移植
```

脚本创建 `content/posts/16-board-port-contract.md`，填写当前带时区的日期、slug、系列和主题，并默认 `draft = true`、`series_confirmed = false`。它拒绝覆盖文件、重复 slug、重复课程编号和未知系列。独立笔记省略 `--series`、`--order` 即可；标题按传入内容保存，不偷偷改写。

写好正文和摘要、完成本课代码验收后，将 `draft` 改为 `false`，执行：

```sh
npm run check
npm run build
python3 tools/blog.py artifact
```

`check` 校验元数据并运行真实 Hugo/工作流/配图测试。`build` 总是生成全新的 `build/release-*/site/`，检查内部文件链接、锚点与草稿排除，并写入文件哈希清单。`artifact` 只返回当前源码对应且文件完整的成功产物目录；失败构建、构建后改源码或修改产物都会被拒绝，不会把旧 PASS 当成新结果。

新增文章会自动进入最新文章、主题标签、订阅和所属系列。课程目录此时显示可点击的“待上线确认”，不会提前打勾。按 [DEPLOYMENT.md](DEPLOYMENT.md) 人工发布、完成 CDN 刷新后运行：

```sh
npm run post:confirm -- board-port-contract
npm run build
```

`confirm` 将实际 HTTPS 文章与本地全新生产构建逐字节比较，成功后才设置 `series_confirmed = true` 并保留核验收据。它不改正文或日期，不上传、不提交、不推送；失败不会设置完成状态。第二次构建自动更新系列总览，再人工部署这份构建即可。测试会验证这一记账变更不改变文章字节。课程代码审查、硬件验收等仍须另行完成，脚本不替代这些判断。

## 增加其他系列

在 `data/series.toml` 登记名称和总览路径，创建对应的 `content/<路径>/_index.md`，front matter 设置 `type = "series"` 和对应 `series_id`。没有课程分组 `parts` 的系列会自动按时间倒序列出文章；普通独立笔记不需要系列配置。

课程分组由 `parts` 的 `id/first/last` 指定，概览正文用 `series-part` shortcode 引用分组。未发布课题放在 `planned` 中，发布后的标题和链接只取自文章。课程编号超出既定范围时先更新课程规划，脚本不会自行改动教学路线。

工作流测试在隔离副本中实际创建草稿、发布待确认文章、访问本地 HTTP 服务器核对正确/错误在线字节、确认后重建；另测第二个系列、独立笔记、重复输入、空成功构建、旧 PASS、源码变更和产物篡改。

可选的 `npm run verify:browser` 会在临时本地服务器上检查当前成功构建的桌面/390px/320px 布局，实际点击系列和主题标签，并验证评论配置。它屏蔽本地预览的第三方请求；`npm run verify:browser -- --url https://blog.xueliangliang.dev/` 则检查线上页面和实际评论 iframe。结果及截图保存在 `build/browser-check/`，不会假定文章数量固定。需先安装 npm 依赖与 Chrome；已有浏览器可用 `PUPPETEER_EXECUTABLE_PATH` 指定，受限环境只对已审查的自有站点显式设置 `BROWSER_NO_SANDBOX=1`。

## 本地预览

```sh
hugo server
```

Hugo 会显示本地预览地址；修改内容后会自动重新构建。

## 手动构建

```sh
hugo version
npm run build
python3 tools/blog.py artifact
```

通过 `artifact` 获取实际产物路径。`hugo --minify` 仍可用于底层调试，但不要把可能残留草稿的旧 `public/` 作为发布输入。本仓库当前测试基线是 Hugo `v0.154.5+extended`；没有 GitHub Actions，构建和部署由维护者手动执行。

系列路线图和术语索引分别位于 `content/series/_index.md`、`content/terms/_index.md`，并通过站点顶部导航访问。文章源文件位于 `content/posts/`，页面模板位于 `layouts/`，样式位于 `static/css/site.css`。`build/`、`public/` 均为生成产物，不提交到 Git。

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
npm run build
```

已有本地 Chrome 时，可用 `PUPPETEER_EXECUTABLE_PATH` 指定其可执行文件。部分 Ubuntu/AppArmor 或容器环境无法启用 Chrome 沙箱；仅渲染自己审查过的本地文章时，可显式使用 `MERMAID_NO_SANDBOX=1 npm run diagrams`。不要以此方式渲染不可信来源。脚本不会关闭系统安全设置，浏览器路径也不写入仓库。

源码与 SVG 不匹配时，Hugo 会报错而不是静默显示旧图。发布前运行 `npm run diagrams:check`；移动端图形支持横向滚动，也可以点击打开原尺寸 SVG。
