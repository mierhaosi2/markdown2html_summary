from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from tools.utils.md_utils import ReportRenderer
from tools.utils.logger_utils import get_logger
from tools.utils.file_utils import get_meta_data
from tools.utils.mimetype_utils import MimeType


class Markdown2htmlTool(Tool):
    logger = get_logger(__name__)

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        raw         = (tool_parameters.get("md_text") or "").strip()
        group_name  = (tool_parameters.get("output_filename") or "").strip()
        prompt_word = (tool_parameters.get("prompt_word") or "").strip()

        try:
            data     = ReportRenderer.parse(raw)
            html_str = ReportRenderer.render(data, group_name=group_name, prompt_word=prompt_word)
        except Exception as e:
            self.logger.exception("Failed to render report")
            yield self.create_text_message(f"Failed to render report HTML, error: {str(e)}")
            return

        yield self.create_blob_message(
            blob=html_str.encode("utf-8"),
            meta=get_meta_data(
                mime_type=MimeType.HTML,
                output_filename=tool_parameters.get("output_filename"),
            ),
        )
        return