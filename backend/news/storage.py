from django.core.files.storage import FileSystemStorage


class PrivateImageStorage(FileSystemStorage):
    """Files are served only by the permission-aware media view, never a static mount."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("file_permissions_mode", 0o600)
        kwargs.setdefault("directory_permissions_mode", 0o700)
        super().__init__(*args, **kwargs)
