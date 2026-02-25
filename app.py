import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr

from cover_letter import generate_cover_letter

_APP_TOKEN = os.getenv("APP_TOKEN", "")


def _sanitize_filename(name: str) -> str:
    """Replace spaces and invalid filesystem chars with underscore."""
    if not name or not name.strip():
        return "cover_letter"
    s = re.sub(r'[<>:"/\\|?*\s]+', "_", name.strip())
    return s or "cover_letter"


def _create_txt_for_download(text: str, company_name: str | None) -> str | None:
    """
    Write the cover letter text to a temp .txt file named <company_name>_<mmdd>.txt
    and return its path for Gradio's DownloadButton.
    """
    cleaned = text.strip()
    if not cleaned:
        return None

    base = _sanitize_filename(company_name or "")
    mmdd = datetime.now().strftime("%m%d")
    filename = f"{base}_{mmdd}.txt"
    tmp_dir = Path(tempfile.gettempdir())
    tmp_path = tmp_dir / filename

    tmp_path.write_text(cleaned, encoding="utf-8")
    return str(tmp_path)


def _extract_file_path(file_obj: Any) -> str | None:
    """
    Best-effort extraction of a filesystem path from Gradio's File component value.
    """
    if file_obj is None:
        return None
    if isinstance(file_obj, (str, Path)):
        return str(file_obj)
    if hasattr(file_obj, "name"):
        return str(file_obj.name)
    if isinstance(file_obj, dict) and "name" in file_obj:
        return str(file_obj["name"])
    return None


def _on_token_change(token: str):
    """Validate the access token and reveal the resume upload on success."""
    if not _APP_TOKEN or token.strip() == _APP_TOKEN:
        return gr.update(visible=True), gr.update(value="", visible=False)
    if token.strip():
        return gr.update(visible=False), gr.update(value="Invalid token.", visible=True)
    return gr.update(visible=False), gr.update(value="", visible=False)


def _on_resume_upload(file_obj) -> dict:
    """Show job description field when a resume is uploaded."""
    return gr.update(visible=file_obj is not None)


def _on_job_description_change(text: str) -> dict:
    """Show model dropdown when job description has content."""
    return gr.update(visible=bool(text and text.strip()))


def _on_model_change(model_name: str | None):
    """Show Generate button when model is selected; hide result actions when model changes."""
    has_model = bool(model_name)
    hide_btn = gr.update(interactive=False, visible=False)
    hide_row = gr.update(visible=False)
    return (
        gr.update(visible=has_model, interactive=has_model),
        hide_btn,
        hide_btn,
        hide_row,
    )


async def _generate_cover_letter_ui(
    resume_file, job_description: str, model_name: str | None
):
    """
    Generator: first yield "Calling <model> API...", then run generation, then yield result.
    """
    hide_btn = gr.update(interactive=False, visible=False)
    show_copy = gr.update(visible=True, interactive=True)
    show_download = gr.update(interactive=True, visible=True)
    show_row = gr.update(visible=True)
    hide_row = gr.update(visible=False)
    show_result_section = gr.update(visible=True)

    no_result = gr.update()
    hide_cover_box = gr.update(visible=False)
    show_cover_box = gr.update(visible=True)
    show_status = gr.update(visible=True, value="")
    hide_status = gr.update(visible=False, value="")

    if not model_name:
        yield ("", "", hide_btn, hide_btn, hide_row, no_result, hide_status, hide_cover_box)
        return
    if resume_file is None or not (job_description or "").strip():
        yield ("", "", hide_btn, hide_btn, hide_row, no_result, hide_status, hide_cover_box)
        return
    resume_path = _extract_file_path(resume_file)
    if not resume_path:
        yield ("", "", hide_btn, hide_btn, hide_row, no_result, hide_status, hide_cover_box)
        return

    # Show only "Calling X API..." message; cover letter box stays hidden
    calling_msg = f"Calling {model_name} API..."
    yield (
        "",
        "",
        hide_btn,
        hide_btn,
        hide_row,
        show_result_section,
        gr.update(visible=True, value=calling_msg),
        hide_cover_box,
    )

    try:
        result = await generate_cover_letter(
            resume_pdf_path=resume_path,
            job_description=job_description,
            model=model_name,
        )
        yield (
            result.cover_letter,
            result.company_name,
            show_download,
            show_copy,
            show_row,
            show_result_section,
            hide_status,
            show_cover_box,
        )
    except Exception as exc:  # noqa: BLE001
        yield (
            f"Error generating cover letter: {exc}",
            "",
            hide_btn,
            hide_btn,
            hide_row,
            show_result_section,
            hide_status,
            show_cover_box,
        )


# Apple system font stack (San Francisco on macOS, Segoe UI on Windows, etc.)
APPLE_FONT_CSS = """
body, .gradio-container, .contain, [class*="block"],
input, textarea, button, select, label {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", sans-serif !important;
}
"""

# Favicon: simple document/letter icon as inline SVG (no external file)
FAVICON_DATA_URL = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect x='4' y='2' width='18' height='28' rx='2' fill='none' stroke='%23333' stroke-width='2'/%3E"
    "%3Cpath d='M8 8h10M8 14h10M8 20h6' fill='none' stroke='%23333' stroke-width='1.5' stroke-linecap='round'/%3E"
    "%3C/svg%3E"
)
PAGE_HEAD = f'<link rel="icon" type="image/svg+xml" href="{FAVICON_DATA_URL}">'

COVER_LETTER_BOX_CSS = """
#generate-btn-row {
    display: flex !important;
    justify-content: center !important;
}
#generate-btn-row > div,
#generate-btn-row button {
    width: auto !important;
    min-width: 100px;
    max-width: 200px;
}
#cover-letter-box { position: relative; }
#cover-letter-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    left: auto !important;
    z-index: 10;
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px;
    margin: 0;
    margin-left: auto !important;
    justify-content: flex-end;
    align-items: center;
    width: auto !important;
    max-width: min-content;
}
#cover-letter-actions > div {
    display: inline-flex !important;
    flex-shrink: 0;
}
/* Force both copy and download to same small size (Gradio wraps them differently) */
#cover-letter-actions button,
#cover-letter-actions .icon-btn,
#cover-letter-actions .icon-btn button,
#cover-letter-actions > div,
#cover-letter-actions > div > button {
    min-width: 32px !important;
    width: 32px !important;
    max-width: 32px !important;
    height: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    font-size: 16px !important;
    line-height: 1 !important;
    flex-shrink: 0 !important;
}
"""


def _build_interface() -> gr.Blocks:
    combined_css = APPLE_FONT_CSS + COVER_LETTER_BOX_CSS
    with gr.Blocks(
        title="Cover Letter Generator",
        head=PAGE_HEAD,
        fill_height=True,
        css=combined_css,
    ) as demo:
        gr.Markdown(
            """
            <h1 style="text-align: center; margin-bottom: 0.25rem;">
                Cover Letter Generator
            </h1>
            <p style="text-align: center; color: #666; font-size: 0.95rem;">
                Upload your resume, paste a job description, and generate a tailored cover letter.
            </p>
            """,
        )

        token_input = gr.Textbox(
            label="Access token",
            placeholder="Enter your access token...",
            type="password",
            visible=bool(_APP_TOKEN),
        )
        token_status = gr.Markdown(value="", visible=False)

        resume_file = gr.File(
            label="Upload resume (PDF)",
            file_types=[".pdf"],
            file_count="single",
            interactive=True,
            visible=not bool(_APP_TOKEN),
        )

        job_description = gr.Textbox(
            label="Job description",
            placeholder="Paste the full job description here...",
            lines=12,
            visible=False,
        )

        model_dropdown = gr.Dropdown(
            label="Model (required)",
            choices=[
                "claude-sonnet-4-0",
                "gpt-5.2",
                "gemini-3-flash-preview",
            ],
            value=None,
            interactive=True,
            visible=False,
        )

        with gr.Row(elem_id="generate-btn-row"):
            generate_btn = gr.Button(
                "Generate",
                variant="primary",
                visible=False,
                scale=0,
            )

        with gr.Column(visible=False, elem_id="result-section") as result_section:
            generating_status = gr.Markdown(
                value="",
                visible=False,
                elem_id="generating-status",
            )
            with gr.Column(visible=False, elem_id="cover-letter-box-wrapper") as cover_letter_box_wrapper:
                with gr.Column(elem_id="cover-letter-box"):
                    cover_letter_output = gr.Textbox(
                        label="Generated cover letter",
                        lines=18,
                    )
                    with gr.Row(elem_id="cover-letter-actions", visible=False) as actions_row:
                        copy_btn = gr.Button(
                            "📋",
                            variant="secondary",
                            scale=0,
                            visible=False,
                            elem_classes=["icon-btn"],
                        )
                        download_btn = gr.DownloadButton(
                            "📥",
                            variant="secondary",
                            scale=0,
                            visible=False,
                            elem_classes=["icon-btn"],
                        )

        copy_status = gr.Markdown(value="", visible=True)
        company_name_state = gr.State(value="")

        # Progressive disclosure: show next field when previous is filled
        token_input.change(
            fn=_on_token_change,
            inputs=token_input,
            outputs=[resume_file, token_status],
        )

        resume_file.change(
            fn=_on_resume_upload,
            inputs=resume_file,
            outputs=job_description,
        )

        job_description.change(
            fn=_on_job_description_change,
            inputs=job_description,
            outputs=model_dropdown,
        )

        model_dropdown.change(
            fn=_on_model_change,
            inputs=model_dropdown,
            outputs=[generate_btn, download_btn, copy_btn, actions_row],
        )

        generate_btn.click(
            fn=_generate_cover_letter_ui,
            inputs=[resume_file, job_description, model_dropdown],
            outputs=[
                cover_letter_output,
                company_name_state,
                download_btn,
                copy_btn,
                actions_row,
                result_section,
                generating_status,
                cover_letter_box_wrapper,
            ],
        )

        download_btn.click(
            fn=_create_txt_for_download,
            inputs=[cover_letter_output, company_name_state],
            outputs=download_btn,
        )

        copy_btn.click(
            fn=lambda t: t,
            inputs=cover_letter_output,
            outputs=copy_status,
            js="(v) => { if (v) navigator.clipboard.writeText(v); return v ? '**Copied to clipboard.**' : ''; }",
        )

    return demo


app = _build_interface()


if __name__ == "__main__":
    app.launch(theme=gr.themes.Soft(), server_name="0.0.0.0")

