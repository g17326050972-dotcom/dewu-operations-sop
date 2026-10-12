import pathlib
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

# Artifact已创建并核验数据；补足其未公开配置的原生整数轴、点标签和图表缓存。
filename = pathlib.Path(sys.argv[1])
ns = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
for prefix in ("c", "a"):
    ET.register_namespace(prefix, ns[prefix])
tag = lambda name: "{" + ns["c"] + "}" + name
with zipfile.ZipFile(filename) as archive:
    files = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    info = archive.infolist()
shared = []
if "xl/sharedStrings.xml" in files:
    shared = ["".join(n.itertext()) for n in ET.fromstring(files["xl/sharedStrings.xml"])]


def cell_value(cell):
    value = cell.find("m:v", ns)
    kind = cell.get("t")
    if kind == "s":
        return shared[int(value.text)]
    if kind == "inlineStr":
        return "".join(cell.find("m:is", ns).itertext())
    if value is None or value.text is None:
        return None
    if kind in ("str", "e", "d"):
        return value.text
    return float(value.text)


workbook = ET.fromstring(files["xl/workbook.xml"])
names = [n.get("name") for n in workbook.find("m:sheets", ns)]
cells = {}
for i, name in enumerate(names, 1):
    xml = ET.fromstring(files["xl/worksheets/sheet%d.xml" % i])
    cells[name] = {n.get("r"): cell_value(n) for n in xml.findall(".//m:c", ns)}


def range_values(formula):
    match = re.fullmatch(r"'([^']+)'!\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)", formula)
    assert match, formula
    sheet, first_column, first, last_column, last = match.groups()
    assert first_column == last_column
    return [cells[sheet].get(first_column + str(i)) for i in range(int(first), int(last) + 1)]


expected_dates = ["10/%02d" % i for i in range(2, 9)]
all_orders = [v for key, v in cells["每日底表"].items() if key.startswith("F") and key[1:].isdigit() and int(key[1:]) >= 7 and isinstance(v, (int, float))]
order_max = max(2, int(max(all_orders)))
chart_files = sorted(n for n in files if re.search(r"/charts/chart\d+\.xml$", n))
assert len(chart_files) == 11
orders_charts = 0
for name in chart_files:
    tree = ET.fromstring(files[name])
    series = tree.find(".//c:ser", ns)
    categories_ref = series.find("c:cat/c:strRef", ns)
    values_ref = series.find("c:val/c:numRef", ns)
    dates = range_values(categories_ref.find("c:f", ns).text)
    values = range_values(values_ref.find("c:f", ns).text)
    assert dates == expected_dates, (name, dates)
    assert len(values) == 7
    for parent, cache_name, data in [(categories_ref, "strCache", dates), (values_ref, "numCache", values)]:
        cache = parent.find("c:" + cache_name, ns)
        if cache is None:
            cache = ET.SubElement(parent, tag(cache_name))
        number_format = cache.find("c:formatCode", ns)
        number_format_text = number_format.text if number_format is not None else "General"
        cache.clear()
        if cache_name == "numCache":
            ET.SubElement(cache, tag("formatCode")).text = number_format_text
        ET.SubElement(cache, tag("ptCount"), {"val": "7"})
        for index, value in enumerate(data):
            if value is None or value == "":
                continue
            pt = ET.SubElement(cache, tag("pt"), {"idx": str(index)})
            ET.SubElement(pt, tag("v")).text = str(value)
    axis = tree.find(".//c:valAx", ns)
    axis_format = axis.find("c:numFmt", ns).get("formatCode")
    series_name = series.find("c:tx/c:v", ns).text
    if series_name == "支付订单数":
        orders_charts += 1
        scaling = axis.find("c:scaling", ns)
        for element, value in [("max", order_max), ("min", 0)]:
            item = scaling.find("c:" + element, ns)
            if item is None:
                item = ET.SubElement(scaling, tag(element))
            item.set("val", str(value))
        unit = axis.find("c:majorUnit", ns)
        if unit is None:
            unit = ET.SubElement(axis, tag("majorUnit"))
        unit.set("val", "1")
    labels = series.find("c:dLbls", ns)
    if labels is None:
        labels = ET.Element(tag("dLbls"))
        series.insert(list(series).index(series.find("c:cat", ns)), labels)
    labels.clear()
    ET.SubElement(labels, tag("numFmt"), {"formatCode": "0.00%" if "%" in axis_format else "#,##0", "sourceLinked": "0"})
    ET.SubElement(labels, tag("dLblPos"), {"val": "t"})
    for key, value in [("showLegendKey", "0"), ("showVal", "1"), ("showCatName", "0"), ("showSerName", "0")]:
        ET.SubElement(labels, tag(key), {"val": value})
    marker = series.find("c:marker", ns)
    if marker is not None:
        marker.find("c:symbol", ns).set("val", "circle")
        size = marker.find("c:size", ns)
        if size is None:
            size = ET.SubElement(marker, tag("size"))
        size.set("val", "5")
    chart = tree.find("c:chart", ns)
    blanks = chart.find("c:dispBlanksAs", ns)
    if blanks is None:
        blanks = ET.SubElement(chart, tag("dispBlanksAs"))
    blanks.set("val", "gap")
    files[name] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
assert orders_charts == 3
temp = filename.with_suffix(".tmp.xlsx")
with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
    for item in info:
        archive.writestr(item, files[item.filename])
temp.replace(filename)
print({"charts": len(chart_files), "date_points_each": 7, "orders_axes": orders_charts, "orders_min": 0, "orders_max": order_max, "orders_major_unit": 1, "native_point_labels": True, "missing_values": "gap"})
