# -*- coding: utf-8 -*-
"""AndroidManifest.xml 解析工具"""

import json
import xml.etree.ElementTree as ET

ANDROID_NS = "http://schemas.android.com/apk/res/android"


def parse_manifest_root(raw_json: str):
    """将 _jeb_call('get_app_manifest') 的返回值解析为 ElementTree root。

    @param raw_json: _jeb_call 返回的 JSON 字符串
    @return: (root, None) 或 (None, error_json_str)
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None, json.dumps({"result": {"success": False, "error": "Failed to parse JEB response"}})
    if "error" in data:
        return None, raw_json
    result = data.get("result")
    # JEB 返回格式可能是字符串或 {"success": true, "manifest": "...xml..."}
    if isinstance(result, dict):
        manifest_text = result.get("manifest")
    else:
        manifest_text = result
    if not manifest_text or not isinstance(manifest_text, str):
        return None, json.dumps({"result": {"success": False, "error": "No manifest text returned"}})
    try:
        root = ET.fromstring(manifest_text)
    except ET.ParseError as e:
        return None, json.dumps({"result": {"success": False, "error": f"XML parse error: {e}"}})
    return root, None


def android_attr(elem, name):
    """获取元素的 android:name 命名空间属性值"""
    return elem.get(f"{{{ANDROID_NS}}}{name}")


def extract_attrs(elem):
    """提取元素的所有属性，去除命名空间 URI 只保留本地属性名"""
    attrs = {}
    for k, v in elem.attrib.items():
        if k.startswith("{"):
            local = k.split("}", 1)[1]
        else:
            local = k
        attrs[local] = v
    return attrs


def extract_intent_filters(elem):
    """提取元素下的所有 intent-filter"""
    filters = []
    for f in elem.findall("intent-filter"):
        entry = {"actions": [], "categories": [], "data": []}
        for action in f.findall("action"):
            name = android_attr(action, "name")
            if name:
                entry["actions"].append(name)
        for cat in f.findall("category"):
            name = android_attr(cat, "name")
            if name:
                entry["categories"].append(name)
        for d in f.findall("data"):
            entry["data"].append(extract_attrs(d))
        filters.append(entry)
    return filters


def extract_meta_data(elem):
    """提取元素下的所有 meta-data"""
    result = []
    for m in elem.findall("meta-data"):
        entry = {
            "name": android_attr(m, "name"),
            "value": android_attr(m, "value"),
            "resource": android_attr(m, "resource"),
        }
        result.append({k: v for k, v in entry.items() if v is not None})
    return result
