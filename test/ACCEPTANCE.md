# WooCsvFix — 验收记录（ACCEPTANCE）

种子缺陷验收（`test/acceptance_test.py`，真实运行结果见 `test/acceptance_results.txt`）：**15/15 PASS**

## 种子缺陷设计（`test/seed_products.csv`，9 个产品行）

自动修复类（期望恰好 5 处）：
1. 价格 `$1,299.00`（货币符号＋千分位逗号）→ 1299.00
2. Type 混合大小写 `Simple` → simple
3. Published `yes` → 1
4. In stock? `yes` → 1
5. Name 首尾空格 → 修剪

阻断类（期望恰好 5 条，只报告不擅改）：
6. SKU 重复（导入器会更新旧产品而非新建）
7. 孤儿变体（Parent SKU 不在文件中）
8. 促销价高于原价
9. 图片为本地路径（非 URL，无法导入）
10. 产品名为空

## 断言口径

- 修复数与阻断数精确相等断言（5/5），消息内容逐条断言
- 行数守恒：9 行进、9 行出，顺序不变，阻断行保留原样
- 复检层只跑自动修复规则：固定文件必须为 0 残留
