import os
from datetime import datetime
from PIL import Image, ImageOps

def generate_new_filename(original_filename):
    """
    アップロードされた画像に対して、衝突を防ぐ一意のファイル名をタイムスタンプから作成します。
    例: sample.jpg -> receipt_20260530_140000.jpg
    """
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = os.path.splitext(original_filename)[1]  # 拡張子 (.jpg など) を取得
    return f"receipt_{now}{ext}"

def resize_image(file_path, max_size=2000):
    """
    画像のEXIF向き（スマホ撮影時の回転情報）を適切に補正し、
    長辺がmax_sizeを超える場合はLANCZOSフィルタを用いて高画質のまま縮小保存します。
    """
    with Image.open(file_path) as img:
        try:
            img = ImageOps.exif_transpose(img)
        except:
            pass

        width, height = img.size
        if max(width, height) > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        img.save(file_path, format="JPEG", quality=85)
