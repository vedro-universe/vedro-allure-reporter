"""
Common utilities for Allure attachments.

This module provides shared functionality for creating and managing Allure attachments
that can be used by both AllureReporter and AllureSteps.
"""

import mimetypes
from mimetypes import guess_extension
from pathlib import Path
from typing import Union

import allure_commons.utils as utils
from allure_commons import plugin_manager
from allure_commons.model2 import ATTACHMENT_PATTERN
from allure_commons.model2 import Attachment as AllureAttachment


def create_attachment(name: str, mime_type: str, ext: str) -> AllureAttachment:
    """
    Create an Allure attachment with the given name, MIME type, and extension.

    Args:
        name: The name of the attachment.
        mime_type: The MIME type of the attachment.
        ext: The file extension of the attachment.

    Returns:
        An AllureAttachment object.
    """
    file_name = ATTACHMENT_PATTERN.format(prefix=utils.uuid4(), ext=ext)
    return AllureAttachment(name=name, source=file_name, type=mime_type)


def create_memory_attachment(data: bytes, name: str, mime_type: str) -> AllureAttachment:
    """
    Create an attachment from in-memory data.

    Args:
        data: The attachment data as bytes.
        name: The name of the attachment.
        mime_type: The MIME type of the attachment.

    Returns:
        The created AllureAttachment object.
    """
    guessed = guess_extension(mime_type)
    ext = guessed.lstrip(".") if guessed else "unknown"
    attachment = create_attachment(name, mime_type, ext)

    plugin_manager.hook.report_attached_data(body=data,
                                             file_name=attachment.source)
    return attachment


def create_text_attachment(text: str, name: str,
                           mime_type: str = "text/plain") -> AllureAttachment:
    """
    Create a text attachment.

    Args:
        text: The text content.
        name: The name of the attachment.
        mime_type: The MIME type (default: "text/plain").

    Returns:
        The created AllureAttachment object.
    """
    return create_memory_attachment(text.encode('utf-8'), name, mime_type)


def create_file_attachment(file_path: Union[str, Path], name: str = None,
                           mime_type: str = None) -> AllureAttachment:
    """
    Create an attachment from a file on disk.

    Args:
        file_path: Path to the file to attach.
        name: Name of the attachment (defaults to filename).
        mime_type: MIME type (auto-detected if not provided).

    Returns:
        The created AllureAttachment object.
    """
    file_path = Path(file_path)

    # Auto-detect MIME type if not provided
    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

    # Use filename as name if not provided
    if name is None:
        name = file_path.name

    # Determine extension
    suffix = file_path.suffix
    ext = suffix.lstrip(".") if suffix else "unknown"

    attachment = create_attachment(name, mime_type, ext)

    plugin_manager.hook.report_attached_file(source=file_path,
                                             file_name=attachment.source)
    return attachment


def create_screenshot_attachment(screenshot_data: bytes,
                                 name: str = "Screenshot") -> AllureAttachment:
    """
    Create a screenshot attachment.

    Args:
        screenshot_data: Raw screenshot data (PNG/JPEG bytes).
        name: Name of the attachment.

    Returns:
        The created AllureAttachment object.
    """
    # Determine format based on header
    if screenshot_data.startswith(b'\x89PNG'):
        mime_type = "image/png"
    elif screenshot_data.startswith(b'\xff\xd8\xff'):
        mime_type = "image/jpeg"
    else:
        mime_type = "image/png"  # Default to PNG

    return create_memory_attachment(screenshot_data, name, mime_type)


def add_attachment_to_step(step_result,
                           attachment: AllureAttachment) -> None:
    """
    Add an attachment to a step result.

    Args:
        step_result: The TestStepResult object.
        attachment: The AllureAttachment to add.
    """
    if (not hasattr(step_result, 'attachments') or
            step_result.attachments is None):
        step_result.attachments = []
    step_result.attachments.append(attachment)
