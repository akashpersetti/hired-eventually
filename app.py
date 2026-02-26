import asyncio
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr

from cover_letter import (
    generate_cover_letter,
    load_applications,
    log_application_to_xlsx,
    mark_application_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_filename(name: str) -> str:
    if not name or not name.strip():
        return "cover_letter"
    s = re.sub(r'[<>:"/\\|?*\s]+', "_", name.strip())
    return s or "cover_letter"


def _create_txt_for_download(text: str, company_name: str | None) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    base = _sanitize_filename(company_name or "")
    mmdd = datetime.now().strftime("%m%d")
    filename = f"{base}_{mmdd}.txt"
    tmp_path = Path(tempfile.gettempdir()) / filename
    tmp_path.write_text(cleaned, encoding="utf-8")
    return str(tmp_path)


def _extract_file_path(file_obj: Any) -> str | None:
    if file_obj is None:
        return None
    if isinstance(file_obj, (str, Path)):
        return str(file_obj)
    if hasattr(file_obj, "name"):
        return str(file_obj.name)
    if isinstance(file_obj, dict) and "name" in file_obj:
        return str(file_obj["name"])
    return None


# ---------------------------------------------------------------------------
# Generate tab — event handlers
# ---------------------------------------------------------------------------

def _on_resume_upload(file_obj):
    return gr.update(visible=file_obj is not None)


def _on_job_description_change(text: str):
    visible = bool(text and text.strip())
    return gr.update(visible=visible), gr.update(visible=visible)


def _on_model_change(model_name: str | None):
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
    resume_file, job_description: str, model_name: str | None, job_link: str
):
    hide_btn = gr.update(interactive=False, visible=False)
    show_copy = gr.update(visible=True, interactive=True)
    show_download = gr.update(interactive=True, visible=True)
    show_row = gr.update(visible=True)
    hide_row = gr.update(visible=False)
    show_result_section = gr.update(visible=True)
    no_result = gr.update()
    hide_cover_box = gr.update(visible=False)
    show_cover_box = gr.update(visible=True)
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

    calling_msg = f"Calling {model_name} API..."
    yield (
        "", "",
        hide_btn, hide_btn, hide_row,
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

        async def _log():
            try:
                await log_application_to_xlsx(
                    company_name=result.company_name,
                    role_applied=result.role_applied,
                    job_id=result.job_id,
                    link=(job_link or "").strip(),
                )
            except Exception as log_exc:
                print(f"[cover-letter-gen] Failed to log to xlsx: {log_exc}")

        asyncio.create_task(_log())

        yield (
            result.cover_letter, result.company_name,
            show_download, show_copy, show_row,
            show_result_section, hide_status, show_cover_box,
        )
    except Exception as exc:  # noqa: BLE001
        yield (
            f"Error generating cover letter: {exc}", "",
            hide_btn, hide_btn, hide_row,
            show_result_section, hide_status, show_cover_box,
        )


# ---------------------------------------------------------------------------
# Applications / Mark tabs — event handlers
# ---------------------------------------------------------------------------

def _load_on_tab_select(evt: gr.SelectData):
    """Reload data when the Applications (index 1) or Mark (index 2) tab is selected."""
    if evt.index in (1, 2):
        rows, choices = load_applications()
        return rows, rows, gr.update(choices=choices, value=None)
    return gr.update(), gr.update(), gr.update()


def _refresh_apps():
    rows, choices = load_applications()
    return rows, gr.update(choices=choices, value=None)


def _refresh_apps_table():
    rows, _ = load_applications()
    return rows


def _do_mark_status(selected: str | None, status: str | None):
    if not selected or not status:
        return "Please select an application and a status.", gr.update(), gr.update()
    row_num = int(selected.split(".")[0])
    msg = mark_application_status(row_num, status)
    rows, choices = load_applications()
    return msg, rows, gr.update(choices=choices, value=None)


# ---------------------------------------------------------------------------
# CSS / assets
# ---------------------------------------------------------------------------

APPLE_FONT_CSS = """
body, .gradio-container, .contain, [class*="block"],
input, textarea, button, select, label {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                 "Segoe UI", Roboto, "Helvetica Neue", sans-serif !important;
}
"""

HEADER_CSS = """
#app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0;
}
#app-header h1 {
    margin: 0;
    font-size: 1.6rem;
}
#sign-out-btn {
    flex-shrink: 0;
}
"""

NAV_CSS = """
#main-nav .tab-nav {
    border-bottom: 2px solid #e0e0e0;
    padding: 0 0.5rem;
}
#main-nav .tab-nav button {
    font-size: 0.92rem;
    font-weight: 500;
    padding: 0.55rem 1.1rem;
}
"""

TABLE_TABS_CSS = """
.refresh-icon-btn {
    min-width: 36px !important; max-width: 36px !important;
    width: 36px !important; height: 36px !important;
    min-height: 36px !important; padding: 0 !important;
    font-size: 18px !important; line-height: 1 !important;
}
#apps-refresh-row, #mark-refresh-row {
    display: flex !important;
    justify-content: flex-end !important;
    margin-top: 4px !important;
}#apps-table .table-wrap,
#mark-table .table-wrap {
    height: auto !important;
    max-height: none !important;
    overflow-y: visible !important;
}
"""

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
    top: 8px; right: 8px; left: auto !important;
    z-index: 10;
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px; margin: 0;
    margin-left: auto !important;
    justify-content: flex-end;
    align-items: center;
    width: auto !important;
    max-width: min-content;
}
#cover-letter-actions > div { display: inline-flex !important; flex-shrink: 0; }
#cover-letter-actions button,
#cover-letter-actions .icon-btn,
#cover-letter-actions .icon-btn button,
#cover-letter-actions > div,
#cover-letter-actions > div > button {
    min-width: 32px !important; width: 32px !important;
    max-width: 32px !important; height: 32px !important;
    min-height: 32px !important; padding: 0 !important;
    font-size: 16px !important; line-height: 1 !important;
    flex-shrink: 0 !important;
}
"""

FAVICON_DATA_URL = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect x='4' y='2' width='18' height='28' rx='2' fill='none' stroke='%23333' stroke-width='2'/%3E"
    "%3Cpath d='M8 8h10M8 14h10M8 20h6' fill='none' stroke='%23333' stroke-width='1.5' stroke-linecap='round'/%3E"
    "%3C/svg%3E"
)
PAGE_HEAD = f'<link rel="icon" type="image/svg+xml" href="{FAVICON_DATA_URL}">'

_COMBINED_CSS = APPLE_FONT_CSS + HEADER_CSS + NAV_CSS + TABLE_TABS_CSS + COVER_LETTER_BOX_CSS


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

def _build_interface() -> gr.Blocks:
    with gr.Blocks(title="Hired (Eventually)") as demo:

        # ── Header: title + sign-out button ─────────────────────────────
        with gr.Row(elem_id="app-header"):
            gr.Markdown(
                "<h1>Hired (Eventually)</h1>",
                elem_id="app-title",
            )
            sign_out_btn = gr.Button(
                "⏻",
                variant="secondary",
                scale=0,
                elem_id="sign-out-btn",
                elem_classes=["refresh-icon-btn"],
            )

        sign_out_btn.click(
            fn=None,
            inputs=[],
            outputs=[],
            js="""() => {
                document.cookie = 'access-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
                document.cookie = 'access-token-unsecure=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
                window.location.reload();
            }""",
        )

        with gr.Tabs(elem_id="main-nav") as main_tabs:

            # ── Tab 1: Generate ──────────────────────────────────────────
            with gr.Tab("Generate Cover Letter"):

                resume_file = gr.File(
                    label="Upload resume (PDF)",
                    file_types=[".pdf"],
                    file_count="single",
                    interactive=True,
                )
                job_description = gr.Textbox(
                    label="Job description",
                    placeholder="Paste the full job description here...",
                    lines=12,
                    visible=False,
                )
                model_dropdown = gr.Dropdown(
                    label="Model (required)",
                    choices=["claude-sonnet-4-0", "gpt-5.2", "gemini-3-flash-preview"],
                    value=None,
                    interactive=True,
                    visible=False,
                )
                job_link_input = gr.Textbox(
                    label="Application link",
                    placeholder="Paste the job application link here...",
                    visible=False,
                )
                with gr.Row(elem_id="generate-btn-row"):
                    generate_btn = gr.Button(
                        "Generate", variant="primary", visible=False, scale=0
                    )

                with gr.Column(visible=False, elem_id="result-section") as result_section:
                    generating_status = gr.Markdown(value="", visible=False)
                    with gr.Column(visible=False, elem_id="cover-letter-box-wrapper") as cover_letter_box_wrapper:
                        with gr.Column(elem_id="cover-letter-box"):
                            cover_letter_output = gr.Textbox(
                                label="Generated cover letter", lines=18
                            )
                            with gr.Row(elem_id="cover-letter-actions", visible=False) as actions_row:
                                copy_btn = gr.Button(
                                    "📋", variant="secondary", scale=0,
                                    visible=False, elem_classes=["icon-btn"],
                                )
                                download_btn = gr.DownloadButton(
                                    "📥", variant="secondary", scale=0,
                                    visible=False, elem_classes=["icon-btn"],
                                )

                copy_status = gr.Markdown(value="", visible=True)
                company_name_state = gr.State(value="")

                resume_file.change(fn=_on_resume_upload, inputs=resume_file, outputs=job_description)
                job_description.change(fn=_on_job_description_change, inputs=job_description, outputs=[model_dropdown, job_link_input])
                model_dropdown.change(fn=_on_model_change, inputs=model_dropdown, outputs=[generate_btn, download_btn, copy_btn, actions_row])
                generate_btn.click(
                    fn=_generate_cover_letter_ui,
                    inputs=[resume_file, job_description, model_dropdown, job_link_input],
                    outputs=[cover_letter_output, company_name_state, download_btn, copy_btn, actions_row, result_section, generating_status, cover_letter_box_wrapper],
                )
                download_btn.click(fn=_create_txt_for_download, inputs=[cover_letter_output, company_name_state], outputs=download_btn)
                copy_btn.click(
                    fn=lambda t: t,
                    inputs=cover_letter_output,
                    outputs=copy_status,
                    js="(v) => { if (v) navigator.clipboard.writeText(v); return v ? '**Copied to clipboard.**' : ''; }",
                )

            # ── Tab 2: Applications ──────────────────────────────────────
            with gr.Tab("Applications"):

                with gr.Row(elem_id="apps-refresh-row"):
                    refresh_btn = gr.Button(
                        "↻", variant="secondary", scale=0,
                        elem_classes=["refresh-icon-btn"],
                    )
                apps_table = gr.Dataframe(
                    headers=["#", "Company", "Role", "Job ID", "Link", "Status"],
                    datatype=["str", "str", "str", "str", "markdown", "str"],
                    interactive=False,
                    wrap=True,
                    elem_id="apps-table",
                )

                refresh_btn.click(fn=_refresh_apps_table, outputs=apps_table)

            # ── Tab 3: Mark Accepted / Rejected ─────────────────────────
            with gr.Tab("Mark Accepted / Rejected"):

                with gr.Row():
                    app_dropdown = gr.Dropdown(
                        label="Select application",
                        choices=[],
                        interactive=True,
                    )
                with gr.Row():
                    accepted_btn = gr.Button("Accepted", variant="primary", scale=0)
                    rejected_btn = gr.Button("Rejected", variant="secondary", scale=0)
                with gr.Row(elem_id="mark-refresh-row"):
                    mark_refresh_btn = gr.Button(
                        "↻", variant="secondary", scale=0,
                        elem_classes=["refresh-icon-btn"],
                    )
                mark_msg = gr.Markdown("")
                mark_table = gr.Dataframe(
                    headers=["#", "Company", "Role", "Job ID", "Link", "Status"],
                    datatype=["str", "str", "str", "str", "markdown", "str"],
                    interactive=False,
                    wrap=True,
                    elem_id="mark-table",
                )

                accepted_btn.click(
                    fn=lambda sel: _do_mark_status(sel, "Accepted"),
                    inputs=[app_dropdown],
                    outputs=[mark_msg, mark_table, app_dropdown],
                )
                rejected_btn.click(
                    fn=lambda sel: _do_mark_status(sel, "Rejected"),
                    inputs=[app_dropdown],
                    outputs=[mark_msg, mark_table, app_dropdown],
                )
                mark_refresh_btn.click(
                    fn=_refresh_apps,
                    outputs=[mark_table, app_dropdown],
                )

        # Load data when Applications or Mark tab is opened
        main_tabs.select(
            fn=_load_on_tab_select,
            outputs=[apps_table, mark_table, app_dropdown],
        )

    return demo


app = _build_interface()

app.launch(
    auth=(os.getenv("APP_USERNAME"), os.getenv("APP_PASSWORD")),
    theme=gr.themes.Soft(),
    css=_COMBINED_CSS,
    head=PAGE_HEAD,
)
