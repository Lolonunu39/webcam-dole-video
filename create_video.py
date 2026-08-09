import os
from ftplib import FTP
import subprocess
from datetime import datetime, timedelta

# ---- CONFIG ----
FTP_HOST = "ftpupload.net"
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

REMOTE_PHOTO_DIR = "/htdocs/photos/"
REMOTE_VIDEO_DIR = "/htdocs/videos/"

LOCAL_IMG_DIR = "images/"
LOCAL_VIDEO_DIR = "videos/"

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
remote_folder = REMOTE_PHOTO_DIR + yesterday + "/"

# ---- 1) Connexion FTP ----
ftp = FTP()
ftp.connect(FTP_HOST, timeout=360)
ftp.login(FTP_USER, FTP_PASS)

print("Connecté au FTP.")

try:
    ftp.cwd(remote_folder)
except:
    print("Dossier introuvable :", remote_folder)
    ftp.quit()
    exit()

files = ftp.nlst()
jpg_files = [f for f in files if f.lower().endswith(".jpg")]

print("Images trouvées :", len(jpg_files))

os.makedirs(LOCAL_IMG_DIR, exist_ok=True)
os.makedirs(LOCAL_VIDEO_DIR, exist_ok=True)

for filename in jpg_files:
    local_path = os.path.join(LOCAL_IMG_DIR, filename)
    with open(local_path, "wb") as f:
        ftp.retrbinary("RETR " + filename, f.write)

print("Téléchargement terminé.")

# ---- 2) Création du filelist ----
filelist_path = os.path.join(LOCAL_IMG_DIR, "filelist.txt")

with open(filelist_path, "w") as f:
    for filename in sorted(jpg_files):
        f.write(f"file '{filename}'\n")
        f.write("duration 2\n")

print("filelist.txt créé.")

# ---- 3) Création de la vidéo ----
video_path = os.path.join(LOCAL_VIDEO_DIR, f"{yesterday}.mp4")

cmd = [
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", filelist_path,
    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    video_path
]

print("Création de la vidéo...")
subprocess.run(cmd)
print("Vidéo créée :", video_path)

# ---- 4) Reconnexion FTP pour éviter le timeout ----
ftp.quit()
ftp = FTP()
ftp.connect(FTP_HOST, timeout=120)
ftp.login(FTP_USER, FTP_PASS)

ftp.cwd(REMOTE_VIDEO_DIR)

with open(video_path, "rb") as f:
    ftp.storbinary(f"STOR {yesterday}.mp4", f)

print("Vidéo envoyée sur InfinityFree !")

# ---- 5) Suppression des images ----
ftp.cwd(remote_folder)

for filename in jpg_files:
    try:
        ftp.delete(filename)
        print("Supprimé :", filename)
    except:
        print("Impossible de supprimer :", filename)

print("Suppression des images terminée.")
ftp.close()
