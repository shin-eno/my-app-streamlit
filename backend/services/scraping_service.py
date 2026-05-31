import os
import re
import shutil
import logging
import requests
from PIL import Image

logger = logging.getLogger(__name__)

class ScrapingService:
    def __init__(self):
        self.webp_extension = ".webp"
        self.jpg_extension = ".jpg"
        self.tmp_dir = "tmp"
        # Dockerコンテナ内の一時作業ディレクトリ
        self.base_working_dir = "/tmp/scraping"

    def execute_scraping_flow(self, url, download_dir_name):
        """スクレイピング、ダウンロード、変換、圧縮の一連の流れを実行する"""
        tmp_dir_path = os.path.join(self.base_working_dir, self.tmp_dir)
        download_dir_path = os.path.join(self.base_working_dir, download_dir_name)

        # フォルダのクリーンアップと作成
        os.makedirs(tmp_dir_path, exist_ok=True)
        os.makedirs(download_dir_path, exist_ok=True)

        try:
            logger.info(f"リンクの解析を開始します URL: {url}")
            image_urls = self._scrape_image_links(url, self.webp_extension)
            logger.info(f"{len(image_urls)} 件のWebP画像リンクを検出しました。")

            for image_url in image_urls:
                dl_filename = image_url[image_url.rfind('/') + 1:]
                tmp_file_path = os.path.join(tmp_dir_path, dl_filename)

                if os.path.isfile(tmp_file_path):
                    continue

                # ダウンロード
                self._file_download(image_url, tmp_file_path)

                # JPG変換
                dest_file_name = os.path.splitext(os.path.basename(dl_filename))[0] + self.jpg_extension
                dest_file_path = os.path.join(download_dir_path, dest_file_name)
                self._convert_webp_to_jpg(tmp_file_path, dest_file_path)

            # ZIPアーカイブ作成
            zip_output_path = os.path.join(self.base_working_dir, download_dir_name)
            shutil.make_archive(zip_output_path, 'zip', root_dir=download_dir_path)
            logger.info(f"ZIPファイルの作成が完了しました: {zip_output_path}.zip")
            
            return f"{zip_output_path}.zip"

        finally:
            # 途中でエラーが起きても一時フォルダは確実に消去する（ディスク圧迫回避）
            if os.path.exists(download_dir_path):
                shutil.rmtree(download_dir_path)
            if os.path.exists(tmp_dir_path):
                shutil.rmtree(tmp_dir_path)

    def _scrape_image_links(self, url, extension):
        dummy_user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'
        response = requests.get(url, headers={"User-Agent": dummy_user_agent}, timeout=10)
        response.raise_for_status()
        regex_pattern = r"https?://[^\s]+{}\b".format(re.escape(extension))
        return re.findall(regex_pattern, response.text)

    def _file_download(self, url, tmp_dl_file_path):
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(tmp_dl_file_path, 'wb') as f:
            f.write(response.content)
        logger.debug(f"Downloaded: {tmp_dl_file_path}")

    def _convert_webp_to_jpg(self, src_file, dest_file):
        with Image.open(src_file) as img:
            rgb_image = img.convert('RGB')
            rgb_image.save(dest_file, 'JPEG')