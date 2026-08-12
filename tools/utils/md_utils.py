import json
import os
from datetime import datetime

_CSS_PATH = os.path.join(os.path.dirname(__file__), "style.css")


def _load_css() -> str:
    with open(_CSS_PATH, "r", encoding="utf-8") as f:
        return f"<style>\n{f.read()}\n</style>"


# SVG icon snippets reused across the template
_ICON_CALENDAR = '<svg class="meta-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 3v3M17 3v3M4 9h16M6 5h12a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'
_ICON_GROUP    = '<svg class="meta-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM2.5 20a5.5 5.5 0 0 1 11 0M16 11a3.5 3.5 0 1 0 0-7M15.5 14.8A5 5 0 0 1 21.5 20" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'
_ICON_CHAT     = '<svg class="meta-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 5h16v11H8l-4 4V5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>'


def _delta_class(text: str) -> str:
    """根据变化文字推断 delta 样式类（up / down / flat）。"""
    if not text:
        return "flat"
    if "↑" in text or "+" in text:
        return "up"
    if "↓" in text or "-" in text:
        return "down"
    return "flat"


class ReportRenderer:
    """将 report_json 字符串或 dict 渲染为周报 HTML。"""

    @staticmethod
    def parse(raw: str) -> dict:
        """解析 JSON 字符串，失败时抛出 ValueError。

        兼容两种结构：
          - 直接周报 dict：{"summary": ..., "key_items": [...], ...}
          - 包装结构：{"report_json": "<周报 JSON 字符串>"}
        """
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("输入必须是 JSON 对象")

        # 展开包装结构：含 report_json 字段时解析其内层字符串
        if isinstance(data.get("report_json"), str):
            try:
                inner = json.loads(data["report_json"])
                if isinstance(inner, dict):
                    return inner
            except json.JSONDecodeError as e:
                raise ValueError(f"report_json 内层解析失败: {e}") from e

        return data

    @classmethod
    def render(cls, data: dict, group_name: str = "", prompt_word: str = "") -> str:
        _g  = str(data.get("group_name", group_name) or group_name) or "客户群"
        _sd = str(data.get("start_date", "") or "")
        _ed = str(data.get("end_date",   "") or "")

        msg_count          = data.get("msg_count")
        participant_count  = data.get("participant_count")
        customer_msg_count = data.get("customer_msg_count")
        ai_response_count  = data.get("ai_response_count")
        msg_count_change    = str(data.get("msg_count_change",    "") or "")
        participant_change  = str(data.get("participant_change",  "") or "")
        ai_response_change  = str(data.get("ai_response_change",  "") or "")
        customer_change    = str(data.get("customer_change",   "") or "")
        summary            = str(data.get("summary", "") or "")
        key_items: list[dict]  = data.get("key_items",  []) or []
        hot_issues: list[dict] = data.get("hot_issues", []) or []
        todos: list[dict]      = data.get("todos",      []) or []

        # ── 头部 meta ──
        period = f"{_sd} — {_ed}" if (_sd and _ed) else (_sd or _ed or "—")
        generated_at = datetime.now().strftime("%Y.%m.%d %H:%M")

        # ── 数据指标 ──
        def _metric(label: str, value, unit: str, change: str) -> str:
            val_html = f'{value}<small>{unit}</small>' if value is not None else '—'
            delta_html = (
                f'<span class="delta {_delta_class(change)}">{change}</span>'
                if change else ""
            )
            return (
                f'<article class="metric">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{val_html}</div>'
                f'{delta_html}'
                f'</article>'
            )

        metrics_html = (
            _metric("消息总数",   msg_count,          "条", msg_count_change)
            + _metric("参与人数", participant_count,  "人", participant_change)
            + _metric("客户消息", customer_msg_count, "条", customer_change)
            + _metric("AI 响应次数", ai_response_count, "次", ai_response_change)
        )

        # ── 总结 ──
        summary_paras = "".join(
            f"<p>{p.strip()}</p>"
            for p in summary.split("\n") if p.strip()
        ) or f"<p>{summary}</p>"

        # ── 重点事项 ──
        topics_html = ""
        for i, item in enumerate(key_items, 1):
            title   = item.get("title",   f"事项 {i}")
            content = item.get("content", "")
            tags    = item.get("tags",    []) or []
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
            topics_html += (
                f'<article class="topic">'
                f'<div class="topic-index">{i:02d}</div>'
                f'<div>'
                f'<div class="topic-title">{title} {tags_html}</div>'
                f'<p class="topic-desc">{content}</p>'
                f'</div>'
                f'</article>'
            )
        if not topics_html:
            topics_html = '<article class="topic"><div class="topic-index">—</div><div><p class="topic-desc">本周暂无重点沟通事项。</p></div></article>'

        # ── 高频问题 ──
        hot_html = ""
        for i, issue in enumerate(hot_issues, 1):
            title = issue.get("title", f"问题 {i}")
            count = issue.get("count", "")
            count_label = f'<span class="hot-count">{count} 次</span>' if count else ""
            hot_html += (
                f'<div class="hot-row">'
                f'<div class="hot-index">{i}</div>'
                f'<div class="hot-title">{title}</div>'
                f'{count_label}'
                f'</div>'
            )
        if not hot_html:
            hot_html = '<div class="hot-row"><div class="hot-title">本周暂无高频问题沉淀。</div></div>'

        # ── 待办事项 ──
        _STATUS_CLASS = {"进行中": "doing", "处理中": "doing", "已完成": "done", "done": "done"}
        todos_html = ""
        for todo in todos:
            content   = todo.get("content", "")
            status    = todo.get("status", "待处理")
            cls_name  = _STATUS_CLASS.get(status, "")
            todos_html += (
                f'<div class="todo-row">'
                f'<span class="check" aria-hidden="true"></span>'
                f'<div class="todo-title">{content}</div>'
                f'<div class="todo-status"><span class="status {cls_name}">{status}</span></div>'
                f'</div>'
            )
        if not todos_html:
            todos_html = (
                '<div class="todo-row">'
                '<span class="check" aria-hidden="true"></span>'
                '<div class="todo-title">暂无待跟进事项</div>'
                '<div class="todo-status">—</div>'
                '</div>'
            )

        footer_text = prompt_word or "本纪要由 AI 根据群聊内容自动整理，请结合实际沟通情况确认。"
        global_css  = _load_css()

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <title>AI 客户群周度纪要</title>
  {global_css}
</head>
<body>
<main class="page">

  <header class="hero">
    <div class="eyebrow">AI 智能纪要</div>
    <h1>周度纪要</h1>
    <div class="meta">
      <span class="meta-item">{_ICON_CALENDAR} 统计周期：{period}</span>
      <span class="meta-item">{_ICON_GROUP} 服务群：{_g}</span>
      <span class="meta-item">{_ICON_CHAT} 生成时间：{generated_at}</span>
    </div>
  </header>

  <section class="section" aria-labelledby="data-title">
    <div class="section-head">
      <h2 class="section-title" id="data-title"><span class="section-no">1</span>沟通数据概览</h2>
      <span class="section-note">与上一统计周期相比</span>
    </div>
    <div class="metric-grid">{metrics_html}</div>
  </section>

  <section class="section" aria-labelledby="summary-title">
    <div class="section-head">
      <h2 class="section-title" id="summary-title"><span class="section-no">2</span>本周沟通总结</h2>
      <span class="section-note">AI 自动归纳</span>
    </div>
    <div class="summary-box">
      <span class="summary-mark">"</span>
      {summary_paras}
    </div>
  </section>

  <section class="section" aria-labelledby="topics-title">
    <div class="section-head">
      <h2 class="section-title" id="topics-title"><span class="section-no">3</span>重点沟通事项</h2>
      <span class="section-note">共 {len(key_items)} 项</span>
    </div>
    <div class="topic-list">{topics_html}</div>
  </section>

  <section class="section" aria-labelledby="todo-title">
    <div class="section-head">
      <h2 class="section-title" id="todo-title"><span class="section-no">5</span>待跟进事项</h2>
      <span class="section-note">共 {len(todos)} 项</span>
    </div>
    <div class="todo-list" role="list">{todos_html}</div>
  </section>

  <footer class="footer">{footer_text}</footer>

</main>
</body>
</html>"""