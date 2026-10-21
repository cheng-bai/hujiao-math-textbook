# 沪教数学教材与交互阅读

五册高中数学教材、教参整合阅读网站，包含教师版与独立学生版、答案显隐、模块化打印、可视化资源与编排工具。

**仓库包含可直接使用的完整预构建网站，不需要 Codex、API Key、登录、数据库或在线公式服务。**

## 下载后直接使用

1. 下载仓库 ZIP 并完整解压，或者 `git clone` 本仓库。
2. 用 Chrome / Edge / Firefox 打开根目录 `index.html`，即可进入五册总目录。
3. 也可以进入 `outputs/五册教材教参整合/index.html`。不要只下载单独一个 HTML 文件。

浏览、公式显示和现有交互所需资源已包含在仓库内。浏览器文件权限有差异，若本地文件模式受限，请使用以下本地服务器。

### 可选：启动本地网站

安装 Python 3.10 或更新版本后，在仓库目录运行：

```sh
python serve.py
```

macOS / Linux 通常使用 `python3 serve.py`。Windows 可双击 `start.bat`；macOS 可在终端执行 `sh start.command`。

默认打开 <http://127.0.0.1:8000/>。端口被占用时执行 `python serve.py --port 8001`。服务器默认仅本机可访问；Ctrl+C 关闭。阅读网站无需执行 `pip install`。

## 功能与使用边界

- 五册总目录：必修第一、二、三册与选择性必修第一、二册，共 101 个节及章末节点。
- 教师页：教材正文、试题、解答及教师批注；可分别隐藏答案和批注。
- 学生页：独立生成，不是教师页隐藏答案后的别名。章节中的“学生包”下载保留，ZIP 解压后离线使用。
- 打印：正文、仅试题、试题与答案、完整内容，并支持题型和范围筛选。
- 可视化：章节内交互模块、资源总览、编排配置导入导出。已有题篮项目未接入。
- 编排状态由当前浏览器保存；换电脑前请导出编排文件，不要依赖本机浏览器状态。

教师版与答案本身在此仓库中公开可见，不能将公开仓库作为考试保密系统。单独分发学生材料时，请使用对应学生 ZIP。

长题若超出一整页，会允许续页；不会通过缩成不可读字号或删除题目来保证“绝不跨页”。不同浏览器、纸张与打印缩放可能改变分页。

## 开发与重建

预构建网站是默认入口。只有修改内容、模板或运行浏览器检查时才需要安装开发依赖（Python 3.10 或更新版本）：

```sh
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell 使用 .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

运行下列命令时以仓库根目录为当前目录。已有脚本也会自行定位仓库，不依赖原作者电脑路径。

```sh
# 从已编辑底稿重建一个章节（保留经过修订的题答）
python scripts/batch_render.py --section batch/sections/x1/x1-2-3.json --force

# 从已编辑底稿重建五册网页及学生下载包
python scripts/batch_render.py --catalog batch/manifests/catalog.json --force

# 检查全部公开文件的路径、资源和学生ZIP
python scripts/check_release.py

# 实际浏览器验证一个章节，包括打印
python scripts/batch_validate.py --section batch/sections/x1/x1-2-3.json --force
```

浏览器检查默认使用 Playwright Chromium；已安装桌面 Chrome 也可作为回退，或设置 `HUJIAO_BROWSER_CHANNEL=chrome`。

`sources/textbooks/` 保存构建使用的教材、教参 Markdown 与题图；`sources/paired/` 保存既有配对清单；`sources/visuals/` 保存圆锥曲线输入。常规编辑从 `batch/sections/` 开始。**不要为了刷新网页重新提取全书**：`batch_extract.py` 是底层原稿提取工具，会重建中间底稿，可能覆盖之后的编辑，应先提交或备份。

来源、资源包与构建记录使用文件字节哈希。根目录 `.gitattributes` 禁止 Git 在检出时自动转换换行，因此 Windows 的 `core.autocrlf` 不会破坏这些哈希。编辑来源文件后，原有哈希不再有效，应重新生成并复核，不能强行忽略来源漂移。

可视化模型测试和生成使用 Node.js 20+；阅读网站、打印和章节渲染不依赖 Node。Anatomy 资源封存工具已包含在 `tools/anatomy/`，不需要安装 Codex skill。

## 目录

| 目录 | 用途 |
| --- | --- |
| `outputs/五册教材教参整合/` | 完整网站、教师/学生页、下载包、公式与图片 |
| `outputs/教材可视化编排小样/` | 独立可视化编排示例 |
| `outputs/教材可视化资源库/` | 版本化交互资源包 |
| `outputs/空间向量基本定理-最小试作/` | 独立教学试作 |
| `scripts/` | 渲染、修复、测试及交互源代码 |
| `batch/sections/` | 已编辑的结构化内容底稿 |
| `batch/patches/`、`batch/reviews/` | 数学修订与历史复核记录 |
| `sources/` | 可重建的输入快照 |
| `designs/` | 早期样章与仍被构建器复用的依赖 |

原工作目录中的大量验证截图、测试打印 PDF、临时解包副本、缓存和本机 SQLite 索引不随源码发布。101 个学生下载 ZIP 是实际功能资源，首版保留，不用 Git LFS。

## 在线部署

此项目是纯静态站点，可部署到任意静态服务器。部署根目录 `index.html`、完整 `outputs/` 和 `batch/reviews/`，保持相对目录结构即可；最后一项供章节的复核记录链接使用。工作流会检查实际部署目录的本地引用，缺少文件时阻止部署。

仓库包含可手动触发的 GitHub Pages 工作流。仓库管理员先在 Settings → Pages 中选择 GitHub Actions，再在 Actions 中运行 **Deploy Pages**。无需开启 Pages 也可下载后本地使用。

## 验证与许可说明

`docs/发布验收说明.md` 记录本次发布测试及限制。旧 `validation.json`、`batch/reviews/` 等记录是历史依据，不表示所有题目重新数学审定，也不表示适用于任意修改后的版本。

项目自有程序代码使用根目录 MIT 许可证，适用范围见 `LICENSE_SCOPE.md`。教材、教参内容及已单独声明许可的第三方资源不因代码开源自动改变许可。已有来源和许可文件保留，第三方组件见 `THIRD_PARTY_NOTICES.md`。
