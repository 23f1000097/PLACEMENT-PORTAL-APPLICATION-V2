import os
from uuid import uuid4

from werkzeug.utils import secure_filename


def save_file(file, upload_folder):
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)

    extension = filename.split(".")[-1]

    unique_name = f"{uuid4().hex}.{extension}"

    path = os.path.join(upload_folder, unique_name)

    file.save(path)

    return unique_name


def success(message, data=None):

    return {
        "success": True,
        "message": message,
        "data": data
    }


def error(message):

    return {
        "success": False,
        "message": message
    }
