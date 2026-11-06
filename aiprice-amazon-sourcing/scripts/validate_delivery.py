#!/usr/bin/env python3
"""Read-only checks for the standard three-file AIPrice delivery (stdlib only)."""

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import posixpath
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
EXPECTED = {
    "Amazon六家公司采集.xlsx",
    "Amazon相似商品首页_长截图_前12项.png",
    "Google Lens 截图_长图_前16项.png",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def company_key(name):
    return re.sub(r"[\s.,，。]", "", name.casefold())


def date_serial(value):
    require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)), "日期须为 YYYY-MM-DD")
    return (dt.date.fromisoformat(value) - dt.date(1899, 12, 30)).days


def image_size(path):
    """Enough header validation to reject empty/wrong files; visual QA is separate."""
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 4 <= len(data):
            if data[i] != 255:
                i += 1
                continue
            while i < len(data) and data[i] == 255:
                i += 1
            if i >= len(data):
                break
            marker = data[i]
            i += 1
            if marker in (0, 1) or 0xD0 <= marker <= 0xD9:
                continue
            length = int.from_bytes(data[i:i + 2], "big")
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", data[i + 3:i + 7])
                return width, height
            if length < 2 or marker == 0xDA:
                break
            i += length
    raise ValueError(f"无法读取 PNG/JPEG 图片尺寸：{path}")


def resolve_part(base, target):
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target))


def relationships(archive, part):
    rel_part = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
    if rel_part not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read(rel_part))
    return {e.get("Id"): resolve_part(part, e.get("Target"))
            for e in root if e.get("TargetMode") != "External"}


def cell_text(cell, shared):
    if cell is None:
        return ""
    raw = cell.findtext("s:v", default="", namespaces=NS)
    if cell.get("t") == "s":
        return shared[int(raw)]
    if cell.get("t") == "inlineStr":
        return "".join(cell.itertext())
    return raw


def verify(data_path, output):
    data = json.loads(data_path.read_text(encoding="utf-8-sig"))
    records = data.get("records", [])
    require(len(records) == 6, "标准交付须有六条已核实公司记录")
    for field in ("collectedDate", "marketplace", "similarUrl", "seedAsin"):
        require(bool(data.get(field)), f"缺少任务字段：{field}")
    date_serial(data["collectedDate"])
    names, orders, asins = [], [], []
    for record in records:
        for field in ("asin", "brand", "seller", "businessName", "businessAddress",
                      "listingDate", "productUrl", "sellerUrl", "screenshotPath"):
            require(isinstance(record.get(field), str) and record[field].strip(),
                    f"原序{record.get('sourceOrder')}缺少字段：{field}")
        require(re.fullmatch(r"[A-Z0-9]{10}", record["asin"]), "ASIN须为10位文本")
        require(type(record.get("sourceOrder")) is int and record["sourceOrder"] > 0,
                "sourceOrder须为正整数")
        price = record.get("priceUSD")
        require(type(price) in (int, float) and math.isfinite(price) and price >= 0,
                "priceUSD须为核实的非负数值")
        days = record.get("listingDays")
        require(days is None or (type(days) is int and days >= 0),
                "listingDays须为插件显示的非负整数或null")
        date_serial(record["listingDate"])
        screenshot = Path(record["screenshotPath"])
        require(screenshot.is_absolute() and screenshot.is_file(), f"详情截图不存在：{screenshot}")
        width, height = image_size(screenshot)
        require(width > 0 and height > 0, "详情截图尺寸无效")
        names.append(company_key(record["businessName"]))
        orders.append(record["sourceOrder"])
        asins.append(record["asin"])
    require(len(set(names)) == 6, "Business Name存在重复；应继续顺序补足")
    require(len(set(asins)) == 6, "六条入选ASIN不应重复")
    require(orders == sorted(set(orders)), "采集原序必须严格递增")
    for skipped in data.get("skipped", []):
        require(skipped.get("duplicateOf") in orders and
                skipped.get("sourceOrder", 0) > skipped["duplicateOf"] and
                skipped.get("sourceOrder") not in orders and skipped.get("reason"),
                "去重跳过记录须指向之前已收录的原序并说明原因")

    actual = {p.name for p in output.iterdir()}
    require(actual == EXPECTED,
            f"结果目录应仅含标准三份文件。缺少：{sorted(EXPECTED - actual)}；多余：{sorted(actual - EXPECTED)}")
    dimensions = {}
    for filename in sorted(EXPECTED - {"Amazon六家公司采集.xlsx"}):
        dimensions[filename] = image_size(output / filename)
        width, height = dimensions[filename]
        require(height > width > 0, f"截图应为可读取的竖向长图：{filename}")

    with zipfile.ZipFile(output / "Amazon六家公司采集.xlsx") as archive:
        wb_part = "xl/workbook.xml"
        workbook = ET.fromstring(archive.read(wb_part))
        require(not any(x.get("date1904") in ("1", "true")
                        for x in workbook.findall("s:workbookPr", NS)),
                "当前数值日期约定使用1900日期系统")
        rels = relationships(archive, wb_part)
        sheets = {s.get("name"): rels[s.get("{" + NS["r"] + "}id")]
                  for s in workbook.findall("s:sheets/s:sheet", NS)}
        require({"商品采集", "采集明细"}.issubset(sheets), "缺少商品采集或采集明细工作表")
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ["".join(t.itertext()) for t in ET.fromstring(
                archive.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        sheet_part = sheets["商品采集"]
        main = ET.fromstring(archive.read(sheet_part))
        cells = {c.get("r"): c for c in main.findall(".//s:sheetData/s:row/s:c", NS)}
        headers = [cell_text(cells.get(f"{col}2"), shared) for col in "BCDEF"]
        require(headers == ["店铺名", "公司名\nASIN", "价格美元", "上架时间", "截图"],
                f"主表列与确认版式不符：{headers}")
        styles = ET.fromstring(archive.read("xl/styles.xml"))
        custom = {int(e.get("numFmtId")): e.get("formatCode")
                  for e in styles.findall("s:numFmts/s:numFmt", NS)}
        xfs = styles.findall("s:cellXfs/s:xf", NS)
        for index, record in enumerate(records, 3):
            display = cell_text(cells.get(f"B{index}"), shared)
            identity = cell_text(cells.get(f"C{index}"), shared)
            require(record["brand"] in display and record["seller"] in display,
                    f"第{index}行店铺/卖家与记录不符")
            require(record["businessName"] in identity and record["asin"] in identity,
                    f"第{index}行公司/ASIN与记录不符")
            for column, expected in (("D", record["priceUSD"]),
                                     ("E", date_serial(record["listingDate"]))):
                cell = cells.get(f"{column}{index}")
                require(cell is not None and cell.get("t", "n") == "n",
                        f"{column}{index}须保存数值，不能为ISO日期或数字文本")
                require(abs(float(cell_text(cell, shared)) - expected) < 0.000001,
                        f"{column}{index}与临时采集记录不符")
            date_cell = cells[f"E{index}"]
            fmt = custom.get(int(xfs[int(date_cell.get("s", "0"))].get("numFmtId", "0")), "")
            require("yyyy-mm-dd" in fmt, f"E{index}未使用短日期显示格式")
            days = record.get("listingDays")
            if days is not None:
                require(f"{days:,}天" in fmt, f"E{index}缺少插件天数显示")

        anchors = []
        sheet_rels = relationships(archive, sheet_part)
        for drawing in main.findall("s:drawing", NS):
            drawing_part = sheet_rels[drawing.get("{" + NS["r"] + "}id")]
            drawing_root = ET.fromstring(archive.read(drawing_part))
            image_rels = relationships(archive, drawing_part)
            for anchor in drawing_root:
                if anchor.find("xdr:pic", NS) is None:
                    continue
                start = anchor.find("xdr:from", NS)
                require(start is not None, "截图缺少单元格定位")
                row = int(start.findtext("xdr:row", namespaces=NS))
                col = int(start.findtext("xdr:col", namespaces=NS))
                anchors.append((row, col))
                blip = anchor.find(".//a:blip", NS)
                image_part = image_rels.get(blip.get("{" + NS["r"] + "}embed")) if blip is not None else None
                require(image_part is not None and len(archive.read(image_part)) > 100,
                        "详情截图未实际嵌入文件")
        require(sorted(anchors) == [(row, 5) for row in range(2, 8)],
                f"主表应在F3:F8各嵌入一张截图，实际定位：{anchors}")
        detail = ET.fromstring(archive.read(sheets["采集明细"]))
        detail_text = "\n".join(cell_text(c, shared) for c in detail.findall(".//s:c", NS))
        for record in records:
            for key in ("businessName", "businessAddress", "productUrl", "sellerUrl"):
                require(record[key] in detail_text, f"采集明细缺少原序{record['sourceOrder']}的{key}")
    return {"status": "结构检查通过，仍需目视核对长图项数及网页数据",
            "companies": 6, "sourceOrder": orders, "screenshots": dimensions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="临时采集JSON，放在结果目录之外")
    parser.add_argument("--output-dir", required=True, type=Path, help="只含最终三份文件的目录")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.data, args.output_dir), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, IndexError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"检查未通过：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
