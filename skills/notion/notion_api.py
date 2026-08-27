#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion REST API 助手（供 notion skill 使用）。

读取凭据：环境变量 NOTION_TOKEN，或 $DSH_HOME/notion/token（默认 ~/.dsh/notion/token）。
仅使用 Python 标准库（urllib），Python 3.9+。
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# 强制 UTF-8 输出：避免 Windows 控制台 GBK 编码在遇到特殊字符（如 U+2068）时崩溃或乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_token():
    t = os.environ.get("NOTION_TOKEN")
    if not t:
        dsh = os.environ.get("DSH_HOME") or str(Path.home() / ".dsh")
        p = Path(dsh) / "notion" / "token"
        if p.exists():
            t = p.read_text(encoding="utf-8").strip()
    if not t:
        sys.exit("NOTION_TOKEN 未配置：请设置环境变量 NOTION_TOKEN，或在 %s 文件中写入 token" % (Path.home() / ".dsh" / "notion" / "token"))
    return t


def call(method, path, payload=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Authorization", "Bearer " + get_token())
    req.add_header("Notion-Version", NOTION_VERSION)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urllib.request.urlopen(req, body, timeout=30) as resp:
            if resp.status == 204:
                return {}
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = {"raw": raw[:500]}
        sys.exit("Notion API HTTP %d: %s" % (e.code, json.dumps(detail, ensure_ascii=False)))
    except urllib.error.URLError as e:
        sys.exit("网络错误: %s" % e.reason)


def get_paginated(path, limit=100):
    """GET 列表端点（blocks children），自动翻页。"""
    items = []
    cursor = None
    while True:
        p = path + ("&" if "?" in path else "?") + "page_size=100"
        if cursor:
            p += "&start_cursor=" + cursor
        data = call("GET", p)
        items.extend(data.get("results", []))
        if not data.get("has_more") or (limit and len(items) >= limit):
            break
        cursor = data.get("next_cursor")
    return items


def post_paginated(path, payload, limit=100):
    """POST 列表端点（search / db query），自动翻页。"""
    items = []
    cursor = None
    while True:
        body = dict(payload or {})
        if cursor:
            body["start_cursor"] = cursor
        remaining = (limit - len(items)) if limit else 100
        body["page_size"] = min(remaining, 100) if remaining > 0 else 1
        data = call("POST", path, body)
        items.extend(data.get("results", []))
        if not data.get("has_more") or (limit and len(items) >= limit):
            break
        cursor = data.get("next_cursor")
    return items


# ---------- 文本转换 ----------

INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)")


def rich_text(md):
    """markdown 行内文本 -> Notion rich_text 数组。"""
    out = []
    for piece in INLINE_RE.split(md):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            out.append({"type": "text", "text": {"content": piece[2:-2]}, "annotations": {"bold": True}})
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            out.append({"type": "text", "text": {"content": piece[1:-1]}, "annotations": {"code": True}})
        elif piece.startswith("[") and "](" in piece:
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", piece)
            if m:
                out.append({"type": "text", "text": {"content": m.group(1), "link": {"url": m.group(2)}}})
            else:
                out.append({"type": "text", "text": {"content": piece}})
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            out.append({"type": "text", "text": {"content": piece[1:-1]}, "annotations": {"italic": True}})
        else:
            out.append({"type": "text", "text": {"content": piece}})
    return out or [{"type": "text", "text": {"content": ""}}]


def block(type_, payload):
    b = {"object": "block", "type": type_}
    b[type_] = payload
    return b


def markdown_to_blocks(md):
    """markdown 文本 -> Notion block 数组。"""
    blocks = []
    code_buf = None
    for line in md.splitlines():
        if line.strip().startswith("```"):
            if code_buf is None:
                code_buf = []
            else:
                blocks.append(block("code", {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_buf)}}],
                    "language": "plain text"}))
                code_buf = None
            continue
        if code_buf is not None:
            code_buf.append(line)
            continue
        s = line.strip()
        if not s:
            continue
        if s == "---":
            blocks.append(block("divider", {}))
        elif re.match(r"^#{1,3} ", s):
            level = len(s) - len(s.lstrip("#"))
            text = s.lstrip("#").strip()
            blocks.append(block("heading_%d" % level, {"rich_text": rich_text(text)}))
        elif re.match(r"^- \[( |x)\] ", s):
            checked = s.startswith("- [x]")
            blocks.append(block("to_do", {"rich_text": rich_text(s[5:]), "checked": checked}))
        elif re.match(r"^[-*] ", s):
            blocks.append(block("bulleted_list_item", {"rich_text": rich_text(s[2:])}))
        elif re.match(r"^\d+\. ", s):
            blocks.append(block("numbered_list_item", {"rich_text": rich_text(re.sub(r"^\d+\. ", "", s))}))
        elif s.startswith("> "):
            blocks.append(block("quote", {"rich_text": rich_text(s[2:])}))
        else:
            blocks.append(block("paragraph", {"rich_text": rich_text(s)}))
    if code_buf is not None:
        blocks.append(block("code", {
            "rich_text": [{"type": "text", "text": {"content": "\n".join(code_buf)}}],
            "language": "plain text"}))
    return blocks


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def block_to_md(block, depth=0):
    t = block.get("type")
    obj = block.get(t) or {}
    texts = "".join(rt.get("plain_text", "") for rt in obj.get("rich_text", []))
    prefix = "  " * depth
    if t == "heading_1":
        return "# " + texts
    if t == "heading_2":
        return "## " + texts
    if t == "heading_3":
        return "### " + texts
    if t == "bulleted_list_item":
        return prefix + "- " + texts
    if t == "numbered_list_item":
        return prefix + "1. " + texts
    if t == "to_do":
        return prefix + "- [%s] " % ("x" if obj.get("checked") else " ") + texts
    if t == "quote":
        return prefix + "> " + texts
    if t == "callout":
        return prefix + "> " + texts
    if t == "code":
        return prefix + "```\n" + texts + "\n```"
    if t == "divider":
        return prefix + "---"
    if t == "child_page":
        return prefix + "# [子页面] " + (obj.get("title") or "")
    if t == "child_database":
        return prefix + "[子数据库] " + (obj.get("title") or "")
    if t == "toggle":
        return prefix + "> " + texts
    return prefix + texts


def prop_to_text(p):
    t = p.get("type")
    v = p.get(t)
    if v is None:
        return ""
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in v)
    if t == "select":
        return (v or {}).get("name", "")
    if t == "multi_select":
        return ", ".join(x.get("name", "") for x in v)
    if t == "status":
        return (v or {}).get("name", "")
    if t == "number":
        return str(v)
    if t == "checkbox":
        return "true" if v else "false"
    if t == "date":
        return (v or {}).get("start", "")
    if t == "url":
        return v or ""
    if t == "email":
        return v or ""
    if t == "phone_number":
        return v or ""
    if t == "people":
        return ", ".join((x.get("name") or x.get("id") or "") for x in v)
    if t in ("created_time", "last_edited_time", "created_by", "last_edited_by", "unique_id"):
        return json.dumps(v, ensure_ascii=False)
    if t == "formula":
        if isinstance(v, dict):
            return str(v.get("string") or v.get("number") or "")
        return str(v)
    return json.dumps(v, ensure_ascii=False)


def page_title(page):
    props = page.get("properties") or {}
    for key, p in props.items():
        if p.get("type") == "title" and p.get("title"):
            return "".join(x.get("plain_text", "") for x in p["title"])
    return "(无标题)"


# ---------- 子命令 ----------

def cmd_whoami(args):
    data = call("GET", "/users/me")
    print(json.dumps({"ok": True, "bot": data.get("name"), "id": data.get("id"),
                      "type": data.get("type"), "workspace": (data.get("bot") or {}).get("workspace_name")},
                     ensure_ascii=False))


def cmd_search(args):
    payload = {"query": args.query} if args.query else {}
    if args.type:
        payload["filter"] = {"value": args.type, "property": "object"}
    results = post_paginated("/search", payload, limit=args.limit)
    for r in results:
        print("%s\t%s\t%s" % (r.get("id"), r.get("object"), page_title(r)))
    print(json.dumps({"ok": True, "count": len(results)}, ensure_ascii=False))


def cmd_page_get(args):
    data = call("GET", "/pages/%s" % args.page)
    props = {}
    for key, p in (data.get("properties") or {}).items():
        props[key] = prop_to_text(p)
    print(json.dumps({"id": data.get("id"), "title": page_title(data),
                      "url": data.get("url"), "properties": props}, ensure_ascii=False, indent=2))


def cmd_page_blocks(args):
    out = []

    def walk(block_id, depth):
        if depth > args.max_depth:
            return
        for b in get_paginated("/blocks/%s/children" % block_id):
            md = block_to_md(b, depth)
            if md:
                out.append(md)
            if b.get("has_children") and b.get("type") in (
                    "bulleted_list_item", "numbered_list_item", "to_do", "quote",
                    "toggle", "paragraph", "callout", "column_list", "synced_block",
                    "child_page", "table"):
                walk(b["id"], depth + 1)

    walk(args.page, 0)
    print("\n".join(out) if out else "(页面无内容块)")


def cmd_page_create(args):
    blocks = markdown_to_blocks(args.body or "")
    first, rest = blocks[:100], blocks[100:]
    payload = {
        "parent": {"page_id": args.parent},
        "properties": {"title": {"title": [{"text": {"content": args.title}}]}},
    }
    if first:
        payload["children"] = first
    data = call("POST", "/pages", payload)
    for chunk in chunks(rest, 100):
        call("PATCH", "/blocks/%s/children" % data["id"], {"children": chunk})
    print(json.dumps({"ok": True, "id": data.get("id"), "url": data.get("url")}, ensure_ascii=False))


def cmd_page_update(args):
    data = call("PATCH", "/pages/%s" % args.id, {
        "properties": {"title": {"title": [{"text": {"content": args.title}}]}}})
    print(json.dumps({"ok": True, "id": data.get("id"), "url": data.get("url")}, ensure_ascii=False))


def cmd_block_append(args):
    blocks = markdown_to_blocks(args.body)
    total = 0
    for chunk in chunks(blocks, 100):
        call("PATCH", "/blocks/%s/children" % args.block, {"children": chunk})
        total += len(chunk)
    print(json.dumps({"ok": True, "block": args.block, "appended": total}, ensure_ascii=False))


def cmd_db_query(args):
    payload = {"page_size": min(args.limit, 100)}
    if args.filter:
        payload["filter"] = json.loads(args.filter)
    if args.sort:
        payload["sorts"] = json.loads(args.sort)
    results = post_paginated("/databases/%s/query" % args.db, payload, limit=args.limit)
    headers = []
    for r in results:
        for key in (r.get("properties") or {}):
            if key not in headers:
                headers.append(key)
    print(" | ".join(headers))
    for r in results:
        vals = []
        for key in headers:
            p = (r.get("properties") or {}).get(key)
            vals.append(prop_to_text(p) if p else "")
        print(" | ".join(vals))
    print(json.dumps({"ok": True, "count": len(results)}, ensure_ascii=False))


def cmd_db_create(args):
    props = json.loads(args.properties) if args.properties else {"Name": {"title": {}}}
    payload = {
        "parent": {"page_id": args.parent},
        "title": [{"type": "text", "text": {"content": args.title}}],
        "properties": props,
    }
    data = call("POST", "/databases", payload)
    print(json.dumps({"ok": True, "id": data.get("id"), "url": data.get("url")}, ensure_ascii=False))


def cmd_db_entry_create(args):
    props = json.loads(args.properties)
    payload = {
        "parent": {"database_id": args.db},
        "properties": props,
    }
    blocks = markdown_to_blocks(args.body or "")
    if blocks:
        payload["children"] = blocks[:100]
    data = call("POST", "/pages", payload)
    rest = blocks[100:]
    for chunk in chunks(rest, 100):
        call("PATCH", "/blocks/%s/children" % data["id"], {"children": chunk})
    print(json.dumps({"ok": True, "id": data.get("id"), "url": data.get("url")}, ensure_ascii=False))


def cmd_db_entry_update(args):
    props = json.loads(args.properties)
    data = call("PATCH", "/pages/%s" % args.entry, {"properties": props})
    print(json.dumps({"ok": True, "id": data.get("id"), "url": data.get("url")}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(prog="notion_api", description="Notion REST API 助手")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("whoami", help="验证 token")
    w.set_defaults(func=cmd_whoami)

    s = sub.add_parser("search", help="搜索页面/数据库")
    s.add_argument("query", nargs="?", default=None)
    s.add_argument("--type", choices=["page", "database"], default=None)
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("page-get", help="读取页面属性")
    g.add_argument("page")
    g.set_defaults(func=cmd_page_get)

    b = sub.add_parser("page-blocks", help="读取页面所有块为 markdown")
    b.add_argument("page")
    b.add_argument("--max-depth", type=int, default=6)
    b.set_defaults(func=cmd_page_blocks)

    c = sub.add_parser("page-create", help="在页面下创建子页面")
    c.add_argument("--parent", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--body", default=None)
    c.set_defaults(func=cmd_page_create)

    u = sub.add_parser("page-update", help="更新页面标题")
    u.add_argument("--id", required=True)
    u.add_argument("--title", required=True)
    u.set_defaults(func=cmd_page_update)

    a = sub.add_parser("block-append", help="向页面/块追加 markdown 内容")
    a.add_argument("--block", required=True)
    a.add_argument("--body", required=True)
    a.set_defaults(func=cmd_block_append)

    q = sub.add_parser("db-query", help="查询数据库")
    q.add_argument("db")
    q.add_argument("--filter", default=None)
    q.add_argument("--sort", default=None)
    q.add_argument("--limit", type=int, default=50)
    q.set_defaults(func=cmd_db_query)

    d = sub.add_parser("db-create", help="创建数据库")
    d.add_argument("--parent", required=True)
    d.add_argument("--title", required=True)
    d.add_argument("--properties", default=None)
    d.set_defaults(func=cmd_db_create)

    e = sub.add_parser("db-entry-create", help="新增数据库条目")
    e.add_argument("--db", required=True)
    e.add_argument("--properties", required=True)
    e.add_argument("--body", default=None)
    e.set_defaults(func=cmd_db_entry_create)

    w = sub.add_parser("db-entry-update", help="更新数据库条目")
    w.add_argument("--entry", required=True)
    w.add_argument("--properties", required=True)
    w.set_defaults(func=cmd_db_entry_update)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
