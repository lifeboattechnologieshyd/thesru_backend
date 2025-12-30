import re
import uuid





def sanitize_filename(filename):
    # Remove unwanted characters and replace spaces with underscores
    sanitized_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    sanitized_filename = sanitized_filename.strip()  # Remove leading/trailing spaces
    return sanitized_filename


def add_unique_suffix_to_filename(filename: str, length=8):
    # Split the filename into name and extension
    filename_list = filename.rsplit(".", 1)
    # Generate a unique UUID hex
    unique_suffix = str(uuid.uuid4().hex)[:length]
    # Combine the name, unique suffix, and extension
    new_filename = (
        f"{filename_list[0]}_{unique_suffix}.{filename_list[1]}"
        if len(filename_list) > 1
        else f"{filename_list[0]}_{unique_suffix}"
    )
    return new_filename