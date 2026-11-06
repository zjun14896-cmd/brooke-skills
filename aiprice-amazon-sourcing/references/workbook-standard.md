# Excel 版式与数据约定

使用当前环境的 spreadsheets 技能和表格工具创建、渲染、导出。已确认的工作簿是展示主表与采集明细两个工作表，不额外生成六张表或六个工作簿。

## 商品采集：五列展示主表

| 列 | 标题 | 内容 |
| --- | --- | --- |
| B | 店铺名 | 相似页展示名/品牌；下一段补充“卖家：...”以区分主体 |
| C | 公司名 / ASIN | Business Name 原文，另起一段列 ASIN |
| D | 价格美元 | 页面核对后的当前美元单价，数值，`0.00` |
| E | 上架时间 | 插件日期及天数，例 `2024-04-20 (930天)` |
| F | 截图 | 对应款真实商品详情页截图，嵌入而非仅链接 |

保留边距 A 列约24px，表头 B2:F2，数据 B3:F8。推荐已验证尺寸：B175、C330、D105、E240、F350px；表头高64px，数据行高202px。正文 Arial 11 加粗、顶部对齐、自动换行；表头 Arial 12白色加粗，深青 `#08777A`；数据行交替 `#CED8DB`、`#E7EBEC`，白色细边框，隐藏网格线，冻结前两行。文字较长时增大行高/列宽，避免截字。

每张图按原始宽高比放进 F 列相应行，留少量边距，常见高度190px，宽度不超过约330px。行高随图片和文字调整。截图可在 Excel 中放大查看；不能把网址或图片文件名当作已嵌入。主表下方可放采集日期、站点、原序及跳过记录的简短说明；完整来源放采集明细。

## 日期兼容：不能出现 ISO 时间串

此流程曾因 Date 对象被导出成 `t="d"`，在用户本地 Excel/WPS 显示 `2022-06-17T00:00:00.000Z`。规避方式：把日期转换为 **Excel数值序列**，再设置日期格式。不要直接传 Date 对象或 ISO 字符串。

```js
const [y, m, d] = listingDate.split('-').map(Number);
const serial = (Date.UTC(y, m - 1, d) - Date.UTC(1899, 11, 30)) / 86400000;
cell.values = [[serial]];
cell.setNumberFormat(`yyyy-mm-dd" (${listingDays.toLocaleString('en-US')}天)"`);
```

日期及天数都取插件实际显示。天数是本次采集快照，不用 TODAY() 更新，也不凭当天重新计算覆盖插件值。若插件只有日期没有天数，用 `yyyy-mm-dd` 并注明天数未显示。日期也未显示时保留“未显示”并报告缺口，不制造日期。价格同样保持数值、两位小数；缺失不能转成0。

检查导出 xlsx 中 E3:E8 的日期值是数值且具有自定义日期格式，没有 `t="d"` 或 ISO时间串。预览确认能显示完整的日期和天数。本地应用行为未重新验证时，不宣称每一种 Excel 版本都已打开测试。

## 采集明细

保留原序、店铺展示名/品牌、卖家、ASIN（文本）、Business Name、Business Address、商品 URL、卖家 URL。另保留去重跳过表：原序、卖家、ASIN、重复于哪条原序、原因。写明采集日期、Amazon站点、沿用的配送国家、实际种子 ASIN/说明、相似页来源。

公司名和地址取卖家页的 Detailed Seller Information 原文。Business Name 可能是个人经营者姓名，保留页面原值，不自行翻译成公司或猜测中文名称。相似页与详情页价格不一致时先核对变体、卖家和配送环境，采用所记录ASIN与卖家的实际价格，并在明细注明差异，不能静默混合。

## 临时数据格式

在交付目录之外保存工作 JSON，供生成表格和结构检查使用。示意结构如下；不是预填新任务的样本答案。

```json
{
  "collectedDate": "YYYY-MM-DD",
  "marketplace": "Amazon.com 美国站",
  "deliveryCountry": "页面当前值",
  "seedAsin": "本次默认第一款ASIN",
  "seedNote": "实际搜索种子的必要说明",
  "similarUrl": "本次相似页URL",
  "records": [
    {
      "sourceOrder": 1,
      "asin": "本次实际ASIN",
      "brand": "相似页展示名",
      "seller": "实际卖家",
      "businessName": "卖家页Business Name原文",
      "businessAddress": "地址各行以换行保留",
      "listingDate": "YYYY-MM-DD",
      "listingDays": 930,
      "priceUSD": 15.99,
      "productUrl": "实际商品URL",
      "sellerUrl": "实际卖家URL",
      "screenshotPath": "临时目录中对应商品截图绝对路径"
    }
  ],
  "skipped": [
    {
      "sourceOrder": 2,
      "asin": "实际跳过ASIN",
      "seller": "实际卖家",
      "duplicateOf": 1,
      "reason": "已核实同一公司"
    }
  ]
}
```

完整成功时 records 正好6条且 sourceOrder 严格递增。Business Name 标准化只辅助去重，JSON及表格仍存原文。

## 最后检查

1. 六家公司已核实且不同，品牌相同不误跳、卖家不同但同公司不重复算。
2. 六条 ASIN、截图、价格、插件日期及卖家对应同一款，原序不变。
3. 工作簿渲染并查看两个表；表头、长公司名、日期及图片均完整。
4. 导出后运行 `python -X utf8 scripts/validate_delivery.py --data 临时JSON --output-dir 结果目录`。它检查当前五列版式的数据、嵌图和日期格式，但不能判断网页内容真假或截图画面完整性。
5. 目视检查 Google Lens16项、Amazon12项两张长图，清理结果目录中的工作文件。只回复最终三件套，不交付临时 JSON 和预览。
