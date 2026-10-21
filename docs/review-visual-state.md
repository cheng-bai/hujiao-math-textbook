# 公共可视化状态逻辑独立复核

- 复核范围：`scripts/visual-book.js`、`scripts/textbook-labs/lab-runtime.js`，并只读核对实际生成册别catalog与构建器接口。
- 方法：静态审查 + Node VM执行真实函数/真实LabTools；本轮未启动浏览器，未修改被审脚本。
- 结论：发现1项会阻断保存/导出的真实错误，已报告并由主代理修复；修复后本轮覆盖的状态逻辑检查通过。

## 发现与修复

默认种子键已变为 `assetId@sectionId`，旧生成方式直接把该键写进 `instanceId`，但实例ID验证只接受字母、数字和连字符。因此默认布局导出会抛错，持久化后再次读取会被当作非法布局清空。

现行代码把实例ID写为 `bundled-assetId-sectionId`，仅在内部播种marker保留`@`；五册默认布局均能通过同一validate再完整读取，不再自我拒绝。

## 跨册/多节/旧布局

- schema为 `hujiao-${BOOK}-visual-layout/v1`，sourceBook同时校验；错误册次或schema拒绝。
- localStorage的x1沿用旧key，其余四册追加册次后缀，不混写不同书。
- 生成catalog按册过滤sections及placements；同一资产跨册/多节可复用，但当前页导入仍须经过本册manifest锚点与兼容节验证。
- 同asset的播种marker包含sectionId；既有逐节marker避免重种，旧x1的module-only marker仍被识别，不会恢复用户先前删除的默认模块。
- 导入先完整validate，再替换当前布局；未知版本、哈希、场景、锚点、重复instanceId、非法参数均不部分应用。

实跑五册的默认种子分别为x1=8、bx1=5、bx2=6、bx3=14、x2=8。测试包含默认布局验证、持久化往返、ID唯一性、跨册拒绝、所有多节placement确被播种、旧module-only marker移除语义、未知state键与非法range步长。共195项VM断言通过。

## Range与hash-json

- 全状态API要求完整键集；checkbox严格布尔、select严格枚举，range为有限数且在上下界内。
- range导入按 `(value-min)/step` 接近整数校验，容差1e-7处理浮点表示，不允许任意范围内的非步长数。
- hash仅在合法math/view/lesson组内做稀疏覆盖；未给键从initial恢复，而不是沿用上次探索值。
- 未知组、未知键、已知键错组、数组/非对象输入及未知scene触发明确提示并恢复默认；不会把错误片段部分写入模型。
- 逐个运行36个真实模块runtime：单控件稀疏恢复、不相关键回默认、非步长拒绝、未知组/键/错组、未知scene与API额外键拒绝，共517项VM断言通过。

## 边界与未覆盖

- 此复核直接执行源脚本中的函数，不修改源文件；未验证实际浏览器存储隔离策略、iframe异步通讯或文件下载。
- 本次状态修复改变公共脚本后，正式输出目录及学生ZIP须重新构建，不能沿用修复前的脚本副本或浏览器验收哈希。
- 当前实际catalog没有“同asset在同一节多个默认锚点”的配置；当前marker设计以asset+节为单位支持本次需求。将来若同一资产在同节自动插入两处，须把marker细化至锚点，但不影响本轮41个默认实例。

## 被审文件 SHA-256

- `scripts/visual-book.js`: `d9699dfd09fbdbcb2a876fa08e8e99d2b1d3b0125452c26afc7d937fa1133db2`
- `scripts/textbook-labs/lab-runtime.js`: `56ed61334ed9efd2e6dbf62b1197596088a594dcb3e0b2224b7f07793aecd8e0`
