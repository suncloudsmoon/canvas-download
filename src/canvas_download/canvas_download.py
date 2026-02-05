"""
canvas-download allows you to download files from canvas with a single command.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from canvasapi import Canvas
from canvasapi.exceptions import Forbidden
from tqdm import tqdm

if sys.platform == "win32":
    import win32api
    import win32con


def get_valid_filename(filename: str):
    return re.sub(r'[<>:"\|\\/\?\*]', " ", filename).strip().strip(".")


def main():
    config_dir = Path(".config")
    login_path = config_dir / "login.json"
    if not config_dir.exists():
        config_dir.mkdir()
        if sys.platform == "win32":
            win32api.SetFileAttributes(str(config_dir), win32con.FILE_ATTRIBUTE_HIDDEN)

        contents = json.dumps({"API_URL": "", "API_KEY": ""}, indent=4)
        login_path.write_text(contents, encoding="utf-8")
        print(
            f"Fill out the details of your canvas login credentials at '{login_path}' and relaunch this application to continue. Note: '.config' directory is hidden."
        )
        return

    contents = login_path.read_text(encoding="utf-8")
    login = json.loads(contents)
    canvas = Canvas(login["API_URL"], login["API_KEY"])

    courses = canvas.get_courses()
    current_courses = [
        course
        for course in courses
        if hasattr(course, "end_at_date")
        and course.end_at_date > datetime.now(tz=timezone.utc)
    ]

    if not current_courses:
        raise LookupError("no enrolled courses found")

    courses_path = config_dir / "courses.json"

    # To get a pretty course name
    names_courses = {}
    for course in current_courses:
        name = course.name
        results = re.search(r"\w\S+-\S+\w", name)
        if results:
            name = results.group(0).replace("-", " ")

        names_courses[name] = course

    if not courses_path.exists():
        config = {k: "modules" for k in names_courses}
        courses_path.write_text(json.dumps(config, indent=4), encoding="utf-8")
        print("Welcome to canvas sync...")
        print("config.json has been created; change settings if needed")
    else:
        contents = courses_path.read_text(encoding="utf-8")
        config = json.loads(contents)
        # config validation
        if not all(name in config for name in names_courses) or not all(
            val.lower() == "modules" or val.lower() == "files"
            for val in config.values()
        ):
            raise ValueError("invalid config")

        for name, course in tqdm(names_courses.items(), desc="Fetching courses"):
            course_path = Path(get_valid_filename(name))
            user_choice = config[name].lower()
            if user_choice == "modules":
                for module in course.get_modules():
                    module_path = course_path / get_valid_filename(module.name)
                    module_path.mkdir(parents=True, exist_ok=True)
                    for item in module.get_module_items():
                        if item.type == "File":
                            file_path = module_path / get_valid_filename(item.title)
                            if not file_path.exists():
                                file = course.get_file(item.content_id)
                                file.download(str(file_path))
            elif user_choice == "files":
                for folder in course.get_folders():
                    folder_name = folder.full_name
                    full_path = Path(folder_name)
                    folder_path = (
                        course_path / full_path.relative_to(full_path.parts[0])
                        if full_path.parts[0] == "course files"
                        else None
                    )
                    folder_path.mkdir(parents=True, exist_ok=True)
                    try:
                        for file in folder.get_files():
                            if file.locked:
                                continue
                            file_path = folder_path / get_valid_filename(file.display_name)
                            if not file_path.exists():
                                file.download(str(file_path))
                    except Forbidden | ResourceDoesNotExist as err:
                        print(err)
