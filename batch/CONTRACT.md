# 五册教材教参网页版批量合同 v1

源资料只读。优先顺序：x1选择性必修第一册，bx1必修第一册，bx2必修第二册，bx3必修第三册，x2选择性必修第二册；排除两本数学建模活动册。

## 文件与写入边界
- parser agent: scripts/batch_extract.py，以及batch/manifests/、batch/sections/。只能自己写这些，不改共享book.css/book.js/build_sample.py。
- renderer agent: scripts/batch_render.py、scripts/batch_validate.py，输出目录 outputs/五册教材教参整合/。不改parser或manifest/section JSON。
- root: batch/CONTRACT.md、scripts/batch_run.py、任务状态、入口与交付说明。
- review agent: batch/reviews/审校JSON及MD，不直接改来源或parser/renderer。

## 中间合同
每节独立JSON: batch/sections/{book_id}/{section_id}.json
字段：schema_version=1, id（册ID+节号避免跨册碰撞）, book_id, book_title, chapter（原章号字符串）, chapter_title, section（如1.1或chapter-end-1）, title, sources={book:绝对MD路径,teacher:绝对MD路径}, source_hashes={绝对路径:SHA256}, blocks, issues。
blocks沿用scripts/build_sample.py现有格式：type(section/heading/prose/question/teacher/editor/intro)，title，markdown，provenance=[{source:book/teacher,start:原行,end:原行}]。
section块含id,number,subtitle；question块含唯一稳定id,category(例题/练习…/习题…),provenance_question,answer,answer_provenance,teacher_analysis,analysis_provenance。teacher/editor应teacher_only=true。缺答案必须显式记录issue，不准猜填、静默错配或由题干冒充答案。
所有Markdown图片先转成来源绝对路径（renderer复制到章节点内并替换成相对路径）；原始src和行号可追溯。其余源文尽量不动。emphases沿用{start,end,kind,title,id}标记已有内容，不重复公式。

manifest: batch/manifests/catalog.json，顶层books数组；每book含id,title,chapters数组；每chapter含id,title,book_source,teacher_source,sections数组；每section含id,section,title,path(项目根相对JSON路径),status,issues摘要。保留章末阅读、内容提要、复习题，作为chapter-end节点，不吞入最后一节或删除。

## 交付与门槛
沿用已认可CSS与打印隔离克隆，教师/学生双版、学生独立ZIP，重点标注；不接题篮。只共享资源且学生包必须自含，不能带答案/教参图/来源。为避免复制整套字体，每册共享vendor资源，学生包再打包所需依赖。
每节源哈希/图片可达/题答数/ID/学生物理隔离/公式渲染必检。打印矩阵共用组件测试一次，逐节仅输出仅试题、题答PDF核分页/裁切；低并发浏览器。疑点记录issues，不以生成或结构通过冒充数学已复核。来源缺口或答案错位为阻塞，不准通过静默删题维持通过率。

## 低上下文与恢复
agent仅读本合同+自己负责脚本+最多1章结构/少量当前节正文；不要读全聊天/全书。每节JSON、构建指纹、检查结果、独立review状态落盘，下一节凭状态继续。构建缓存键含源哈希、section JSON、模板/资源版本；无变更的已通过节点跳过。制作和复核写不同文件。错误先隔离，不阻塞别节。报告最多简短数字+阻塞ID，长明细写文件。
