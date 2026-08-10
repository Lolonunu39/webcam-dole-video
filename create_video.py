import os
import sys
from ftplib import FTP
import subprocess
from datetime import datetime, timedelta
import zoneinfo  # Inclus dans Python 3.9+

# ---- CONFIG ----
FTP_HOST = os.getenv("FTP_HOST", "ftpupload.net")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

# Heure de Paris pour éviter les décalages avec le serveur GitHub (UTC)
tz_paris = zoneinfo.ZoneInfo("Europe/Paris")
now_paris = datetime.now(tz_paris)

# Si le script tourne après minuit (ex: 00:05), la journée traitée est celle d'hier
yesterday = (now_paris - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"Traitement du dossier de la journée : {yesterday}")

REMOTE_PHOTO_DIR = f"htdocs/photos/{yesterday}"
REMOTE_VIDEO_DIR = "htdocs/videos"

LOCAL_IMG_DIR = "images"
LOCAL_VIDEO_DIR = "videos"

# ---- 1) Connexion FTP ----
ftp = FTP()
ftp.connect(FTP_HOST, timeout=360)
ftp.login(FTP_USER, FTP_PASS)
print("Connecté au FTP.")

try:
    ftp.cwd(REMOTE_PHOTO_DIR)
except Exception as e:
    print(f"Dossier introuvable : {REMOTE_PHOTO_DIR}. Erreur: {e}")
    ftp.quit()
    sys.exit(0)  # Fin propre sans crash de l'action si aucune photo n'a été prise

files = []
ftp.retrlines('NLST', files.append)
jpg_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg'))]

print(f"Images trouvées ({len(jpg_files)}) :", jpg_files)

if not jpg_files:
    print("Aucune image à traiter.")
    ftp.quit()
    sys.exit(0)

os.makedirs(LOCAL_IMG_DIR, exist_ok=True)
os.makedirs(LOCAL_VIDEO_DIR, exist_ok=True)

# Téléchargement des images
for filename in sorted(jpg_files):
    local_path = os.path.join(LOCAL_IMG_DIR, filename)
    with open(local_path, "wb") as f:
        ftp.retrbinary("RETR " + filename, f.write)

print("Téléchargement terminé.")

# ---- 2) Création du filelist ----
filelist_path = os.path.join(LOCAL_IMG_DIR, "filelist.txt")
with open(filelist_path, "w") as f:
    for filename in sorted(jpg_files):
        f.write(f"file '{filename}'\n")
        f.write("duration 0.5\n") # Ajustez la durée par image (ex: 0.5s = 2 images/sec)

# ---- 3) Création de la vidéo ----
video_path = os.path.join(LOCAL_VIDEO_DIR, f"{yesterday}.mp4")

cmd = [
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", filelist_path,
    "-vf", "scale=1280:-2",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "28",
    "-pix_fmt", "yuv420p",
    video_path
]

print("Création de la vidéo avec FFmpeg...")
subprocess.run(cmd, check=True)
print("Vidéo créée :", video_path)

# ---- 4) Upload de la vidéo sur FTP ----
ftp.cwd("/") # Retour à la racine FTP
try:
    ftp.cwd(REMOTE_VIDEO_DIR)
except:
    ftp.mkd(REMOTE_VIDEO_DIR)
    ftp.cwd(REMOTE_VIDEO_DIR)

with open(video_path, "rb") as f:
    ftp.storbinary(f"STOR {yesterday}.mp4", f)

print("Vidéo envoyée sur InfinityFree !")

# ---- 5) Suppression des images du serveur FTP ----
ftp.cwd("/")
ftp.cwd(REMOTE_PHOTO_DIR)

for filename in jpg_files:
    try:
        ftp.delete(filename)
    except Exception as e:
        print(f"Erreur lors de la suppression de {filename}: {e}")

print("Suppression des images terminée.")
ftp.quit()
