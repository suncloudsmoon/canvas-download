"""
Create a file called login.json with the following:
{
    "API_URL": "",
    "API_KEY": ""
}
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from canvasapi import Canvas
from tqdm import tqdm


def get_valid_filename(filename: str):
    return re.sub(r'[<>:"\|\\/\?\*]', " ", filename).strip()


login_path = Path(__file__).parent / "login.json"
login = json.loads(login_path.read_text(encoding="utf-8"))
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

config_path = Path("config.json")
names_courses = {
    re.search(r"\w\S+-\S+\w", course.name).group(0).replace("-", " "): course
    for course in current_courses
}
if not config_path.exists():
    config = {k: "modules" for k in names_courses}
    config_path.write_text(json.dumps(config, indent=4), encoding="utf-8")
    print("Welcome to canvas sync...")
    print("config.json has been created; change settings if needed")
else:
    contents = config_path.read_text(encoding="utf-8")
    config = json.loads(contents)
    # config validation
    if not all(name in config for name in names_courses) or not all(
        val.lower() == "modules" or val.lower() == "files" for val in config.values()
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
                full_path = Path(folder.full_name)
                folder_path = (
                    course_path / full_path.relative_to(full_path.parts[0])
                    if full_path.parts[0] == "course files"
                    else None
                )
                folder_path.mkdir(parents=True, exist_ok=True)
                for file in folder.get_files():
                    if file.locked:
                        continue
                    file_path = folder_path / get_valid_filename(file.display_name)
                    if not file_path.exists():
                        file.download(str(file_path))
