"""Alert dispatcher for pipeline failures and degraded data quality."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def build_alert_message(
    dag_id: str,
    task_id: str,
    execution_date: datetime,
    exception: Exception | None,
    log_url: str,
) -> str:
    lines = [
        f"*Pipeline Failure*",
        f"DAG: `{dag_id}`",
        f"Task: `{task_id}`",
        f"Execution: `{execution_date.isoformat() if hasattr(execution_date, 'isoformat') else execution_date}`",
        f"Log: {log_url}",
    ]
    if exception:
        lines.append(f"Error: `{str(exception)[:300]}`")
    return "\n".join(lines)


def send_slack_alert(message: str, webhook_url: str | None = None) -> None:
    try:
        from slack_sdk.webhook import WebhookClient
    except ImportError:
        return

    url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return

    client = WebhookClient(url)
    client.send(
        attachments=[
            {
                "color": "danger",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message},
                    }
                ],
            }
        ]
    )


def send_email_alert(message: str, subject: str | None = None, to: str | None = None) -> None:
    try:
        from airflow.utils.email import send_email as airflow_send_email
    except ImportError:
        return

    recipient = to or os.getenv("ALERT_EMAIL")
    if not recipient:
        return

    airflow_send_email(
        to=recipient,
        subject=subject or "[Alt Pipeline FAILURE]",
        html_content=message.replace("\n", "<br>"),
    )


def alert_on_failure(context: dict) -> None:
    dag_id = context["dag"].dag_id
    task_id = context["task"].task_id
    execution_date = context["execution_date"]
    exception = context.get("exception")
    log_url = context["task_instance"].log_url

    message = build_alert_message(dag_id, task_id, execution_date, exception, log_url)
    subject = f"[Alt Pipeline FAILURE] {dag_id}.{task_id}"

    send_slack_alert(message)
    send_email_alert(message, subject=subject)
