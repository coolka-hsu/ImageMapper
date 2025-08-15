# utils/uploader.py
import os
import uuid
import logging
import shutil
from pathlib import Path
from typing import Optional

# ========= 環境控制 =========
FORCE_DEST = os.getenv("UPLOAD_DEST", "").strip().lower()  # "cloudinary" | "local" | ""
LOCAL_STATIC_DIR = Path(os.getenv("LOCAL_STATIC_DIR", "static/images"))
LOCAL_STATIC_DIR.mkdir(parents=True, exist_ok=True)

# 是否具備 Cloudinary 憑證
_HAS_URL = bool(os.getenv("CLOUDINARY_URL"))
_HAS_TRIPLE = all(
    os.getenv(k) for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
)
_CLOUDINARY_ENABLED = _HAS_URL or _HAS_TRIPLE

try:
    import cloudinary
    import cloudinary.uploader as cu
    import cloudinary.api as ca
    from cloudinary.exceptions import Error as CloudinaryError
    _CLOUDINARY_IMPORTED = True
except Exception as e:
    _CLOUDINARY_IMPORTED = False
    logging.warning(f"Cloudinary import failed: {e}")

def _cloudinary_config():
    """初始化 Cloudinary 設定（支援 CLOUDINARY_URL 或三件式憑證）"""
    if not (_CLOUDINARY_IMPORTED and _CLOUDINARY_ENABLED):
        return False
    try:
        if _HAS_URL:
            # 會自動讀取 CLOUDINARY_URL
            cloudinary.config()
        else:
            cloudinary.config(
                cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                api_key=os.getenv("CLOUDINARY_API_KEY"),
                api_secret=os.getenv("CLOUDINARY_API_SECRET"),
                secure=True,
            )
        return True
    except Exception as e:
        logging.error(f"Cloudinary config error: {e}")
        return False

# ========= 對外主入口 =========
def upload_image(image_path: str, public_id: Optional[str] = None, public_id_prefix: str = "slice") -> str:
    """
    上傳圖片：優先 Cloudinary（若可用），否則落地本機 /static/images。
    參數：
      - image_path: 本機暫存檔路徑（建議放 /tmp）
      - public_id: 指定雲端 public_id（不含副檔名）
      - public_id_prefix: 未指定 public_id 時，用 prefix + uuid 組成
    回傳：可公開存取的 URL
      - Cloudinary：secure_url
      - 本機："/static/images/xxx.png"（相對路徑，不帶網域）
    """
    # 強制目的地
    if FORCE_DEST == "cloudinary":
        try:
            return _upload_to_cloudinary(image_path, public_id, public_id_prefix)
        except Exception as e:
            logging.error(f"Cloudinary forced but failed: {e}")
            raise
    if FORCE_DEST == "local":
        return _upload_to_local(image_path, public_id, public_id_prefix)

    # 自動路徑：能用雲端就上雲，否則本機
    if _cloudinary_config():
        try:
            return _upload_to_cloudinary(image_path, public_id, public_id_prefix)
        except Exception as e:
            logging.error(f"Cloudinary upload failed, fallback to local. Reason: {e}")

    # fallback: local
    return _upload_to_local(image_path, public_id, public_id_prefix)

# ========= 舊名稱相容（保留你的函式名） =========
def upload_to_cloudinary(image_path, public_id=None):
    return _upload_to_cloudinary(image_path, public_id, "slice")

def upload_to_local_storage(image_path, public_id=None):
    return _upload_to_local(image_path, public_id, "slice")

# ========= 內部實作 =========
def _upload_to_cloudinary(image_path: str, public_id: Optional[str], public_id_prefix: str) -> str:
    if not _cloudinary_config():
        raise RuntimeError("Cloudinary not configured/imported")

    # 目錄（夾）名稱
    folder = os.getenv("CLOUDINARY_FOLDER", "imagemapper").strip() or None

    # 決定 public_id
    if not public_id:
        public_id = f"{public_id_prefix}_{uuid.uuid4().hex}"

    # 上傳
    try:
        resp = cu.upload(
            image_path,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        url = resp.get("secure_url") or resp.get("url")
        if not url:
            raise RuntimeError(f"Cloudinary response has no URL: {resp}")
        logging.info(f"Uploaded to Cloudinary: {url}")
        return url
    except CloudinaryError as ce:
        raise RuntimeError(f"CloudinaryError: {ce}") from ce
    except Exception as e:
        raise RuntimeError(f"Cloudinary upload exception: {e}") from e

def _upload_to_local(image_path: str, public_id: Optional[str], public_id_prefix: str) -> str:
    # 準備檔名
    ext = Path(image_path).suffix or ".png"
    if public_id:
        filename = f"{public_id}{ext}"
    else:
        filename = f"{public_id_prefix}_{uuid.uuid4().hex}{ext}"

    dest = LOCAL_STATIC_DIR / filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    # 優先 move（更快）；失敗再 copy2
    try:
        shutil.move(image_path, dest)
    except Exception:
        shutil.copy2(image_path, dest)

    # 回傳相對路徑，避免在雲端環境硬編 localhost
    rel_url = f"/static/images/{dest.name}"
    logging.info(f"Stored locally: {rel_url}")
    return rel_url

def delete_from_cloudinary(public_id: str) -> bool:
    """刪除雲端圖片（僅 Cloudinary）"""
    if not _cloudinary_config():
        logging.warning("delete_from_cloudinary called but Cloudinary not configured.")
        return False
    try:
        resp = cu.destroy(public_id)
        return resp.get("result") == "ok"
    except Exception as e:
        logging.error(f"Error deleting from Cloudinary: {e}")
        return False

def get_cloudinary_status() -> dict:
    """回傳 Cloudinary 設定狀態"""
    status = {
        "imported": _CLOUDINARY_IMPORTED,
        "has_url": _HAS_URL,
        "has_triple": _HAS_TRIPLE,
        "configured": False,
        "message": "",
    }
    if not (_CLOUDINARY_IMPORTED and _CLOUDINARY_ENABLED):
        status["message"] = "Cloudinary not imported or credentials missing"
        return status
    if not _cloudinary_config():
        status["message"] = "Cloudinary config failed"
        return status
    try:
        ca.ping()
        status.update({"configured": True, "message": "Cloudinary is properly configured"})
    except Exception as e:
        status["message"] = f"Cloudinary ping failed: {e}"
    return status
