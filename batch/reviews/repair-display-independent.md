# 显示修订独立复核

复核方式：只读检查共享实现，在内存中调用 `approved_section`；以独立图片替换器、数学token扫描器及从验证器AST抽出的实际allowlist表达式进行测试。没有运行extract／render，没有改公共代码。

## 发现与复验状态

### 已修复的P2：学生ZIP allowlist曾信任整个vendor-katex目录前缀

位置：`scripts/batch_validate.py:215`。

首次复核时，表达式允许任何 `vendor-katex/` 前缀条目，不只允许来自实际KaTeX供应目录的文件。将以下文件名加入一个原本合格的选修一学生包名字列表，旧检查表达式仍返回True：

- `vendor-katex/private-answers.json`
- `vendor-katex/../../teacher.html`

这不是已观察到的教师内容泄漏：首次只读检查当前101个学生ZIP均通过，未发现teacher命名资源或旧 `module-data.js`。已由主agent改为供应目录实际文件精确集合，检查集合相等、重复项、绝对路径、父路径与反斜线。独立抽取更新后的实际AST表达式复验：101现有学生ZIP均通过；注入 `teacher.html`、旧教师module-data、conic教师payload、伪装vendor私有JSON、vendor父路径、绝对路径、反斜线以及重复 `student.html` 共8个反例均被拒绝。此项已关闭。

### 编辑补写的答案依据复验

独立从AST载入更新后的 `has_answer_basis`，没有导入或运行验证流程。两种正例（`answer_editorial.kind=independently-derived`并有reason；`editorial_answer.status=authored`并有basis）均通过；缺编辑标识、缺题面来源、缺独立推导理由、缺补写basis的四个反例均拒绝。扫描当前bx1/bx2/bx3全部题块，没有缺失有效答案依据的题块。此改动允许明确标注的编辑补写，不要求伪造原教参行号。

## 8.1／8.2 emphasis修复验证

| 节 | 全部标注数 | 边界数 | 涉及正文中的数学token | 切断数学token的修复后边界 |
| --- | ---: | ---: | ---: | ---: |
| 8.1 | 8 | 16 | 178 | 0 |
| 8.2 | 11 | 22 | 145 | 0 |

独立验证结果：

1. 对原样章JSON使用独立实现展开图片路径，与 `approved_section` 返回内容对比；除emphases偏移字段外，正文、题面、公式及其他字段一致。
2. 全部19处标注内的原样章文字，经同一来源路径转换后，与修复后截取片段完全一致；38个边界均在合法范围内，没有切断数学token。
3. 当前8.1、8.2中间底稿的所有emphases与内存重建结果一致，覆盖不止patch列出的四个变更块。
4. 对四个变更块，将旧偏移重新作用于当前正文，能重现15个切断数学token的旧边界；换成新偏移后全部消失。因此这次不是只隐藏报错，确实修正了偏移原因。
5. `repair-display-emphases.json`保留四块标注前后值；修复脚本只改emphases，不改markdown。脚本正常重跑在无漂移时不新增证据、不产生新改动。

6. 最新脚本先在内存收集两节staged payload，再检查旧证据是否允许发布，之后才写底稿，已避免“先改底稿、后因证据存在而报错”的半写问题；无变化时不重写底稿。此项为代码路径独立复核。

通用边界：当前变换按“完整图片链接替换后，重新计算前缀长度”重定位，适用于本次全部标注。若将来出现标注边界落在图片链接内部，应额外拒绝／校正，不应假定前缀替换总能表达其意图；本次未发现该情况。

## 可视化等待逻辑

- `ready()`先等页面math初始化，再等 `dataset.visualReady`，最后等正文中所有可视化加载状态隐藏，顺序正确。
- `visual-book.js`在完成宿主插入后才置visualReady，而iframe异步就绪另由状态隐藏保证；因此只等页面load导致的早期计数／截图竞争已被覆盖。
- 没有可视化落点的正常节也会执行 `renderCurrent()` 并置ready；若manifest不存在或节ID不匹配则超时，能暴露实际资源问题，而不是静默通过。
- 所有五册及离线学生HTML均有manifest和visual-book脚本引用；新增等待没有明显对正常空模块节造成必然超时。

这部分为代码与调用链复核，不冒充本轮重新进行了101节真实浏览器回归。

## 学生资源隔离的实际结果

使用本次验证器的真实AST表达式只读核对当前101个ZIP：101通过，无teacher命名载荷。以下常见误混资源的注入均被拒绝：`teacher.html`、`visual-assets/module-data.js`、`visual-assets/conic-hyperbola-teacher.js`。`visual_files(data, True)`对圆锥曲线选择学生专用payload，未把教师payload放入正常允许集合。

最终结论：emphasis修复通过独立核验，visualReady等待逻辑合理；当前学生包未见教师命名payload。allowlist的vendor前缀豁免已修复，恶意条目反例全部拒绝；新增编辑补写依据判断通过正反例复验。本报告范围内无未关闭发现。
