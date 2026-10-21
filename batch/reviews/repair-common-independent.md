# 公共修复独立复核（内容脚本与结构验证）

复核范围：`repair_display_sections.py`、`batch_extract.approved_section` 的强调边界重定位、`batch_validate.has_answer_basis`、等待条件与学生ZIP隔离。未重复全量浏览器；最终CSS及PDF证据待主agent补充后续读。

## 已验证

- 对8.1/8.2原样章与`approved_section`逐块比较：19个强调区间均在有效范围，边界不落在图片Markdown内部，重定位前后选中文本逐字相同。正式bx2底稿所有相关emphases与修复后的approved_section结果一致。不是仅验证偏移量非负。
- 图链扩展前后的下标使用Python字符索引，和原JSON所存start/end一致；以转换后prefix长度重算，不把路径字符增长误当正文变化。
- 实际调用`has_answer_basis`检查全选修二356道题块通过。唯一没有来源答案的`x2-5-3-p534-1`现含`answer_editorial.kind=independently-derived`和明确reason；保留原`editor_revision`及空`answer_provenance`，不假造教参行号。
- 10个x2修复节点的698个来源引用均存在且行号在真实文件范围内，来源哈希全部不变。回源答案与编辑推导以`【回源配对并编辑补解】/【编辑订正】/【编辑补写】`标识；来源行号指原结果/题设依据，不宣称新补解逐字见于原教参。
- `ready`依次等待主页面load、数学渲染状态出现、visualReady以及当前正文可视化加载状态消失，随后等待document.fonts.ready。随后逐版明确检查数学错误数组、图片自然尺寸和JS异常，不以“等待函数返回”冒充成功。
- 学生ZIP在解压前核对CRC、精确文件集合、无重复、无绝对/父级/反斜线路径，排除teacher载荷、原module-data.js、源资料与private图。解压到独立临时目录后file://离线运行，重复检查公式、图片及题数。来源验证与学生物理隔离是独立检查项。

原始结构检查记录：`batch/reviews/repair-common-independent-data.json`。

## 一个可改进点（不影响当前已修复文件）

`repair_display_sections.py`在循环内先写回底稿，循环结束后才检查已有`repair-display-emphases.json`是否允许再写证据。当前重跑无改动，因此不会触发问题；但若未来底稿重新出现需要修复的偏移且旧证据仍在，脚本会先写数据再assert拒绝证据，导致部分应用后报错。建议先计算两节全部变更并预检证据文件，再批量写入；或把新一轮证据带版本追加。此项只读报告，未改共享脚本。

## 边界

`has_answer_basis`是结构门槛，有非空来源引用或明确编辑补写元数据即可；不会自行核对每条数学推导。行号有效也不等于来源语义吻合，x2语义回源和数值复算另见author/selfcheck记录；独立数学交叉审校由另一agent负责。当前重定位函数没有为“强调边界落在图片链接内部”的未来输入定义特殊规则，但本轮19条均不属于此情形。

## 最终打印规则补审

已只读核对主agent的最终`book.js`、`book.css`：

- JS只在生成打印副本时计数`.question-body img`，至少4图才加`print-compact-figures`；题解图片不参与计数，原阅读DOM不添加该类。
- 本轮101个底稿的题干图片计数扫描，只有`bx3-chapter-end-11-hA-1`一题满足条件（5图），因此这次34mm规则的实际影响范围不是全书所有插图。
- CSS将打印副本内该类的题干图片最大高度由40mm限为34mm，仍继承`width:auto;height:auto;max-width:100%`。没有设置裁剪容器、定宽定高拉伸、object-fit:cover或overflow:hidden；因此是保比例缩放，而不是截去图边或轴标。
- `#print-output .question{display:flow-root}`只作用于打印容器（及打印预览），不作用于阅读正文题块。它建立块格式化上下文，包含末尾子块margin，针对根因修复“正文结束后尾margin撑出空白页”，没有删段落、删题或隐藏图片。
- 两条规则保留`break-inside:avoid-page`/`page-break-inside:avoid`及整题题干的`print-question-head`，没有通过强制裁切模拟不跨页。单页装不下的长题仍可能合理续页；具体通过以PDF标记检查为准。

边界：最大高度从40mm到34mm会使这道多图题中的图中文字最多缩小约15%，虽然不会裁切，仍需实际PDF抽看标注可读性。不能据DOM测量或CSS规则声称任意浏览器、缩放和打印机都不跨页。主agent报告的Chrome实际分页证据以及最终回归结果用于交付结论，本复核没有另起全量浏览器。

原脚本证据预检问题已复核关闭：`repair_display_sections.py`现先stage两节全部payload并验证已有证据，再写证据和底稿；不再在拒绝旧证据前写回底稿。当前逻辑无变更时不写底稿，幂等边界更明确。

## 折叠原文公式计数与五册缓存补审

`rendered_source_formula_count`是从真实`.book-body`深克隆后操作：在副本内用`.visual-original-body`的完整子节点替换折叠外壳，再删除独立`.visual-module`，最后统计`.katex`。与`visual-book.js`原文存储结构逐项核对一致；既不只统计可见摘要，也不修改真实阅读DOM。`teacher/student_formula_count_and_errors`仍把计数相等与`window.__mathErrors`为空作为两个同时成立的条件；解压学生包采用同样标准。

直接提取当前函数中的JS，在小型内存DOM契约模型执行11项测试，全部通过：

- 折叠摘要复制的重点卡及模块附加公式不重复计数；完整原文、题干、答案与分析各计一次。
- 真实DOM序列化内容在调用前后逐字相同。
- 原文公式未渲染、原文公式被删除、答案公式被删除，计数均少1，不能被摘要副本补足。
- 原文额外公式仍被统计；摘要额外复制公式则不计；学生与零公式页面行为正确。
- 即便数量正确，非空数学错误数组仍使验收条件失败。

记录：`batch/reviews/repair-common-formula-count-test.json`。本测试执行实际JS函数，不调用浏览器；它验证克隆/移除/计数的逻辑契约，不能替代Chrome的DOM实现和真实页面测试。主agent已运行x1圆锥三节真实回归，此处不重复争用浏览器。

`batch_run.fingerprint`现在以`book_id in PRIORITY`覆盖x1、bx1、bx2、bx3、x2，五册都加入`visual-book.css`、`visual-book.js`及`visual-assets`直属文件内容/文件名。使用实际fingerprint函数与隔离内存文件系统，对五册逐一模拟修改视觉CSS、视觉JS及资源payload，共15个指纹变化测试全部通过；还原依赖后基线指纹一致。记录：`batch/reviews/repair-common-fingerprint-test.json`。

缓存范围边界：当前实现对任意视觉资源改动会保守使五册指纹失效，安全但不是最细粒度；`glob('*')`只覆盖直属文件，当前生成载荷均为直属，未来若把依赖移入子目录需要递归或manifest依赖枚举。公式数量是结构检查，不是逐条TeX身份/数学意义证明；模块自己的iframe公式由专项可视化验证负责，这次源正文计数不会把模块公式混作教材原文。
