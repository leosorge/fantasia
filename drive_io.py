"""Accesso a Drive con OAuth utente o service account su Drive condiviso."""
import io
import json
import os
from pathlib import Path

DOC = "application/vnd.google-apps.document"
FOLDER = "application/vnd.google-apps.folder"
SCOPE = "https://www.googleapis.com/auth/drive"
NEW_ID = "1uHM0g_0uIfg0YRi_l2uG6-mRrUQCPrOP"
OLD_ID = "1QC0G1NlVVfQCf1nLX6Q85g2Kxmm0EkaE"
OLD_TXT_ID = "1noKbzSbLnK4VUjWYo7y4DgJ6eL7EdQC2"


def category_specification(content, names):
    marker = "CATEGORIE AMMESSE\n"
    example = "ESEMPIO (DATI FITTIZI)"
    if example not in content:
        raise ValueError("fantasia_formato.txt: intestazione ESEMPIO assente")
    intro, remainder = content.split(example, 1)
    if marker in intro:
        intro = intro.split(marker, 1)[0]
    section = marker + "\n".join(f"- {name}" for name in names)
    section += "\n- Canali seguiti (assegnata automaticamente ai video dei canali monitorati)"
    return intro.rstrip() + "\n\n" + section + "\n\n" + example + remainder


def query_literal(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def supported(file):
    mime = file["mimeType"]
    return (mime == DOC or mime.startswith("text/") or
            mime == "application/octet-stream" and Path(file["name"]).suffix.lower() in {".txt", ".md"})


class DriveManager:
    def __init__(self, service=None):
        if service is None:
            import google.auth
            from google.oauth2 import credentials, service_account
            from googleapiclient.discovery import build
            raw = os.getenv("FANTASIA_DRIVE_CREDENTIALS")
            if raw:
                info = json.loads(raw)
                if info["type"] == "service_account":
                    auth = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
                else:
                    auth = credentials.Credentials.from_authorized_user_info(info, scopes=[SCOPE])
            else:
                auth, _ = google.auth.default(scopes=[SCOPE])
            service = build("drive", "v3", credentials=auth, cache_discovery=False)
        self.files = service.files()
        self.new_id = os.getenv("FANTASIA_NEW_ID") or NEW_ID
        self.old_id = os.getenv("FANTASIA_OLD_ID") or OLD_ID
        self.old_txt_id = os.getenv("FANTASIA_OLD_TXT_ID") or OLD_TXT_ID
        self.shared_drive = os.getenv("FANTASIA_SHARED_DRIVE_ID")
        if len({self.new_id, self.old_id, self.old_txt_id}) != 3:
            raise ValueError("La coda e l’archivio devono essere cartelle distinte.")

    def validate(self):
        for folder in (self.new_id, self.old_id, self.old_txt_id):
            data = self.files.get(fileId=folder, supportsAllDrives=True, fields="mimeType,trashed").execute()
            if data.get("trashed") or data["mimeType"] != FOLDER:
                raise ValueError("Configurazione Drive: cartella assente o non utilizzabile.")

    def list_files(self, query, fields):
        token = None
        while True:
            params = {"corpora": "drive", "driveId": self.shared_drive} if self.shared_drive else {}
            data = self.files.list(q=query, fields=f"nextPageToken,files({fields})",
                                   pageToken=token, pageSize=100,
                                   includeItemsFromAllDrives=True, supportsAllDrives=True,
                                   **params).execute(num_retries=3)
            yield from data.get("files", [])
            token = data.get("nextPageToken")
            if not token:
                break

    def list_new(self):
        query = f"{query_literal(self.new_id)} in parents and trashed=false and mimeType != '{FOLDER}'"
        items = list(self.list_files(query, "id,name,mimeType,createdTime,version"))
        return sorted(items, key=lambda item: (item.get("createdTime", ""), item["id"]))

    def read(self, item):
        from googleapiclient.http import MediaIoBaseDownload
        if item["mimeType"] == DOC:
            request = self.files.export_media(fileId=item["id"], mimeType="text/plain")
        else:
            request = self.files.get_media(fileId=item["id"], supportsAllDrives=True)
        buffer = io.BytesIO()
        download = MediaIoBaseDownload(buffer, request, chunksize=256 * 1024)
        done = False
        while not done:
            _, done = download.next_chunk(num_retries=3)
            if buffer.tell() > 1_000_000:
                raise ValueError("testo oltre 1 MB")
        return buffer.getvalue().decode("utf-8-sig")

    def archive(self, key, filename, html):
        from googleapiclient.http import MediaIoBaseUpload
        literal = query_literal(key)
        query = (f"{query_literal(self.old_id)} in parents and trashed=false and "
                 f"appProperties has {{ key='fantasiaArchive' and value={literal} }}")
        if next(self.list_files(query, "id"), None):
            return
        name_query = (f"{query_literal(self.old_id)} in parents and trashed=false and "
                      f"name = {query_literal(filename)}")
        if next(self.list_files(name_query, "id"), None):
            path = Path(filename)
            filename = f"{path.stem}_{key[:8]}{path.suffix}"
        body = {"name": filename, "parents": [self.old_id],
                "appProperties": {"fantasiaArchive": key}}
        media = MediaIoBaseUpload(io.BytesIO(html.encode("utf-8")), mimetype="text/html", resumable=False)
        self.files.create(body=body, media_body=media, supportsAllDrives=True, fields="id").execute()

    def archive_text(self, key, content):
        from googleapiclient.http import MediaIoBaseUpload
        name = f"{key}.txt"
        query = (f"{query_literal(self.old_txt_id)} in parents and trashed=false and "
                 f"name = {query_literal(name)}")
        if next(self.list_files(query, "id"), None):
            return
        media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=False)
        self.files.create(body={"name": name, "parents": [self.old_txt_id]},
                          media_body=media, supportsAllDrives=True, fields="id").execute()

    def sync_category_specification(self, names):
        from googleapiclient.http import MediaIoBaseUpload
        file_id = "12c80du4uaN_PxbwGA52sYppWhnxlfaIK"
        current = self.read({"id": file_id, "mimeType": "text/plain"})
        updated = category_specification(current, names)
        if updated != current:
            media = MediaIoBaseUpload(io.BytesIO(updated.encode("utf-8")), mimetype="text/plain", resumable=False)
            self.files.update(fileId=file_id, media_body=media, supportsAllDrives=True,
                              fields="id").execute(num_retries=3)

    def has_video(self, video_id):
        query = f"appProperties has {{ key='fantasiaVideo' and value={query_literal(video_id)} }}"
        return next(self.list_files(query, "id"), None) is not None

    def enqueue_video(self, video_id, filename, content):
        from googleapiclient.http import MediaIoBaseUpload
        if self.has_video(video_id):
            return False
        body = {"name": filename, "parents": [self.new_id],
                "appProperties": {"fantasiaVideo": video_id}}
        media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")),
                                  mimetype="text/plain", resumable=False)
        self.files.create(body=body, media_body=media, supportsAllDrives=True, fields="id").execute()
        return True

    def acknowledge(self, item):
        current = self.files.get(fileId=item["id"], supportsAllDrives=True,
                                 fields="parents,version,trashed").execute(num_retries=3)
        if (current.get("trashed") or self.new_id not in current.get("parents", []) or
                current.get("version") != item.get("version")):
            return False
        self.files.update(fileId=item["id"], body={"trashed": True},
                          supportsAllDrives=True, fields="id").execute(num_retries=3)
        return True
