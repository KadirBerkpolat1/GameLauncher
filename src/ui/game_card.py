from PySide6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QDialog, QListWidget, QListWidgetItem, QDialogButtonBox)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QUrl, Signal, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from src.utils.async_utils import get_async_loop

def get_installed_game_path(app_id: int):
    from src.utils.paths import get_steam_libraries
    from pathlib import Path
    import vdf
    for lib in get_steam_libraries():
        acf = Path(lib) / "steamapps" / f"appmanifest_{app_id}.acf"
        if acf.exists():
            try:
                with open(acf, 'r', encoding='utf-8') as f:
                    data = vdf.load(f)
                    installdir = data.get("AppState", {}).get("installdir", "")
                    if installdir:
                        return str(Path(lib) / "steamapps" / "common" / installdir)
            except:
                pass
    return None


def _titles_match(found: str, expected: str) -> bool:
    """online-fix.me basligi ile kullanici oyun adini normalize edip karsilastirir."""
    import html as _html
    import re as _re
    def norm(s: str) -> str:
        return _re.sub(r"[\W_]+", "", _html.unescape(s).lower().strip())
    fn, en = norm(found), norm(expected)
    return bool(fn and (fn == en or fn in en or en in fn))


class _GamePickDialog(QDialog):
    """online-fix.me arama sonuclari arasindan dogru oyunu sectirir."""

    def __init__(self, results: list, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fix Kaynağını Seçin")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)

        lbl = QLabel("online-fix.me'de şu oyunlar bulundu. Doğru olanı seçin:")
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        for r in results:
            item = QListWidgetItem(r.get("title") or r.get("url", ""))
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.list_widget.addItem(item)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected(self) -> dict:
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else {}

class GameCard(QFrame):
    """
    A visual card representing a single game in the library or search results.
    Fetches the cover art natively using QNetworkAccessManager.
    """
    download_requested = Signal(int, str)
    uninstalled = Signal(int)
    image_load_failed = Signal(object)

    def __init__(self, app_id: int, title: str, image_url: str = "", mode: str = "search") -> None:
        super().__init__()
        self.app_id = app_id
        self.title = title
        self.image_url = image_url
        self.mode = mode
        self.setObjectName("GameCard")
        # Enlarge card to fit 2:3 aspect ratio covers and vertical buttons
        self.setFixedSize(240, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(5)

        # Image Label
        self.image_label = QLabel()
        self.image_label.setObjectName("GameCardImage")
        self.image_label.setStyleSheet("background-color: #1B2027; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self.image_label.setFixedSize(240, 360)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("Loading...")
        layout.addWidget(self.image_label)

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; padding: 0 10px; color: #FFFFFF;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Action Buttons (Contextual based on mode)
        btn_layout = QVBoxLayout() if self.mode == "library" else QHBoxLayout()
        btn_layout.setContentsMargins(10, 0, 10, 0)

        if self.mode == "search":
            self.btn_download = QPushButton("Add to Library")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._add_to_library)

            btn_layout.addWidget(self.btn_download)
        elif self.mode == "store":
            self.badge = QLabel("Available", self.image_label)
            self.badge.setStyleSheet("background-color: #238636; color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            self.badge.move(175, 10)

            self.btn_download = QPushButton("Add to Library")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._add_to_library)

            btn_layout.addWidget(self.btn_download)
        elif self.mode == "queued":
            self.btn_commit = QPushButton("Download")
            self.btn_commit.setProperty("cssClass", "PrimaryAction")
            self.btn_commit.clicked.connect(self._commit_and_download)

            self.btn_remove = QPushButton("Remove")
            self.btn_remove.setProperty("cssClass", "SecondaryAction")
            self.btn_remove.clicked.connect(self._remove_from_queue)

            btn_layout.addWidget(self.btn_remove)
            btn_layout.addWidget(self.btn_commit)
        elif self.mode == "library":
            installed_path = get_installed_game_path(self.app_id)
            self._installed_path = installed_path
            
            btn_text = "Uninstall" if installed_path else "Delete Lua"
            self.btn_uninstall = QPushButton(btn_text)
            self.btn_uninstall.setProperty("cssClass", "SecondaryAction")
            self.btn_uninstall.setStyleSheet("background-color: #DA3633; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600;")
            self.btn_uninstall.clicked.connect(self._uninstall_game)

            self.btn_download = QPushButton("Download")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._request_download)

            btn_layout.addWidget(self.btn_uninstall)
            btn_layout.addWidget(self.btn_download)
            if installed_path:
                self.btn_apply_fix = QPushButton("Apply Fix")
                self.btn_apply_fix.clicked.connect(self._apply_fix_auto)
                btn_layout.addWidget(self.btn_apply_fix)
        layout.addLayout(btn_layout)

        # Network Manager for Image Downloading
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_image_loaded)

        if self.app_id and self.app_id != 0:
            self._fetch_image()
        else:
            self.image_label.setText("No Image")

    def _fetch_image(self, index: int = 0) -> None:
        if not hasattr(self, 'image_urls'):
            self.image_urls = [
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{self.app_id}/library_600x900.jpg",
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{self.app_id}/header.jpg",
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{self.app_id}/capsule_616x353.jpg",
            ]
            if self.image_url and self.image_url not in self.image_urls:
                self.image_urls.append(self.image_url)

        if index == 0:
            from src.config.settings import SettingsManager
            sgdb_key = SettingsManager.get("steamgriddb_api_key", "")
            if sgdb_key:
                get_async_loop().create_task(self._resolve_and_fetch_sgdb(sgdb_key))
                return

        self._start_network_fetch(index)

    async def _resolve_and_fetch_sgdb(self, api_key: str) -> None:
        try:
            import httpx
            # v2 endpoint: grids/game/{appid} — eski grids/game/steam/{appid}
            # formatı artık 404 dönüyor.
            url = f"https://www.steamgriddb.com/api/v2/grids/game/{self.app_id}?dimensions=600x900"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("data"):
                        # En yüksek topluluk skorlu grid'i seç
                        grids = sorted(
                            data["data"],
                            key=lambda g: g.get("score", 0),
                            reverse=True,
                        )
                        sgdb_image_url = grids[0]["url"]
                        self.image_urls.insert(0, sgdb_image_url)
                else:
                    print(
                        f"SteamGridDB API {resp.status_code} for {self.app_id}, "
                        "falling back to Steam CDN"
                    )
        except Exception as e:
            print(f"SteamGridDB API error for {self.app_id}: {e}")

        # Her durumda fallback'e düş: hata, boş sonuç, geçersiz anahtar...
        self._start_network_fetch(0)

    def _start_network_fetch(self, index: int) -> None:
        if index < len(self.image_urls):
            self.current_url_index = index
            request = QNetworkRequest(QUrl(self.image_urls[index]))
            self.network_manager.get(request)
        else:
            if not getattr(self, '_steam_fallback_tried', False):
                self._steam_fallback_tried = True
                get_async_loop().create_task(self._fetch_steam_api_fallback())
            else:
                self.image_label.setText("No Image Available")
                self.image_load_failed.emit(self)

    async def _fetch_steam_api_fallback(self) -> None:
        try:
            import httpx
            url = f"https://store.steampowered.com/api/appdetails?appids={self.app_id}"
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    app_data = data.get(str(self.app_id), {})
                    if app_data.get("success") and "data" in app_data:
                        game_data = app_data["data"]
                        fallback_img = game_data.get("header_image") or game_data.get("capsule_image")
                        if fallback_img and fallback_img not in self.image_urls:
                            self.image_urls.append(fallback_img)
                            self._start_network_fetch(len(self.image_urls) - 1)
                            return
        except Exception as e:
            print(f"Steam API fallback error for {self.app_id}: {e}")
        
        self.image_label.setText("No Image Available")
        self.image_load_failed.emit(self)

    def _on_image_loaded(self, reply: QNetworkReply) -> None:
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if reply.error() == QNetworkReply.NetworkError.NoError and status_code == 200:
            image_data = reply.readAll()
            image = QImage()
            image.loadFromData(image_data)

            pixmap = QPixmap(image).scaled(
                240, 360,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
            self.image_label.setText("")
        else:
            self._fetch_image(getattr(self, 'current_url_index', 0) + 1)

        reply.deleteLater()
    def _add_to_library(self) -> None:
        self.btn_download.setText("Adding...")
        self.btn_download.setEnabled(False)
        
        loop = get_async_loop()
        loop.create_task(self._async_add_to_library())
        
    async def _async_add_to_library(self) -> None:
        try:
            from src.services.download import DownloadManager
            # prepare_game_data fetches the lua and updates SLSsteamConfigManager
            await DownloadManager.prepare_game_data(self.app_id, scope="full")
            self.btn_download.setText("Added to Library")
            self.btn_download.setStyleSheet("background-color: #238636; color: white;")
        except Exception as e:
            self.btn_download.setText("Error")
            self.btn_download.setEnabled(True)
            print(f"Error adding to library: {e}")
            
    def _request_download(self) -> None:
        self.download_requested.emit(self.app_id, self.title)

    def _apply_fix_auto(self) -> None:
        """
        Apply Fix: once internetten (online-fix.me) oyunun fix arşivini çekmeyi
        dener; başarısız olursa yerel assets/onlinefix şablonuna düşer.
        Steam çalışıyorsa önce kapatılır, yama sonrası yeniden başlatılır.
        """
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        from pathlib import Path
        import subprocess

        target_path = getattr(self, '_installed_path', None)

        if not target_path or not Path(target_path).exists():
            default_dir = str(Path.home() / ".local/share/Steam/steamapps/common")
            target_path = QFileDialog.getExistingDirectory(self, "Oyun Klasörünü Seçin", default_dir)

        if not target_path:
            return

        self._fix_target_path = target_path
        self.btn_apply_fix.setEnabled(False)
        self.btn_apply_fix.setText("Steam Kapatılıyor...")

        res = subprocess.run(["pgrep", "-x", "steam"], capture_output=True)
        if res.returncode == 0:
            subprocess.run(["steam", "-shutdown"], check=False)
            QTimer.singleShot(4000, self._start_fix_download)
        else:
            self._start_fix_download()

    def _start_fix_download(self) -> None:
        self.btn_apply_fix.setText("Fix çekiliyor...")
        get_async_loop().create_task(self._async_fetch_and_apply_fix())

    async def _async_fetch_and_apply_fix(self) -> None:
        """
        Async akış: oyun ara -> hosters linkini bul -> fix seç -> indir -> uygula.
        Hata olursa yerel şablondan uygular.
        """
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        from urllib.parse import urlparse, unquote

        from PySide6.QtWidgets import QMessageBox

        from src.api.onlinefix import OnlineFixClient, OnlineFixError, OnlineFixNotFoundError
        from src.utils.onlinefix_patcher import OnlineFixPatcher

        target_path = getattr(self, '_fix_target_path', None)
        if not target_path:
            return

        client = OnlineFixClient()
        downloaded = None
        extracted_tmp = None
        used_online = False
        try:
            self.btn_apply_fix.setText("Oyun aranıyor...")
            results = await client.search_game(self.title)
            if not results:
                raise OnlineFixNotFoundError("Oyun online-fix.me'de bulunamadı.")

            # Birden fazla sonuç varsa kullanıcı seçer (yanlış fix riski sıfırlanır).
            if len(results) > 1:
                dlg = _GamePickDialog(results, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                picked = dlg.selected()
                if not picked.get("url"):
                    return
                game_url = picked["url"]
            else:
                game_url = results[0]["url"]
                found_title = results[0].get("title", "")
                if found_title and not _titles_match(found_title, self.title):
                    box = QMessageBox(self)
                    box.setWindowTitle("Oyun Eşleşmedi")
                    box.setIcon(QMessageBox.Icon.Warning)
                    box.setText(
                        f"online-fix.me'de bulunan oyun:\n<b>{found_title}</b>\n\n"
                        f"Sizin seçiminiz:\n<b>{self.title}</b>\n\n"
                        "Yine de bu fix'i indirip uygulamak ister misiniz?"
                    )
                    btn_yes = box.addButton("Evet, uygula", QMessageBox.ButtonRole.AcceptRole)
                    box.addButton("Hayır, iptal", QMessageBox.ButtonRole.RejectRole)
                    box.exec()
                    if box.clickedButton() is not btn_yes:
                        return

            self.btn_apply_fix.setText("İndirme linkleri alınıyor...")
            page = await client.get_game_page(game_url)
            hoster_url = page.get("hoster_link")
            if not hoster_url:
                raise OnlineFixNotFoundError("Hoster bağlantısı bulunamadı.")

            game_name = unquote(urlparse(hoster_url).path.strip("/"))
            entries = await client.get_fix_entries(game_name)
            fix = client.pick_fix(entries)
            if not fix:
                raise OnlineFixNotFoundError("Güvenli fix dosyası bulunamadı.")

            direct, cookies = await client.resolve_direct(fix)
            dest = os.path.join(tempfile.gettempdir(), f"ofme_{self.app_id}_{fix['file_name']}")
            self.btn_apply_fix.setText(f"İndiriliyor: {fix['file_name'][:24]}")
            await client.download(direct, dest, cookies)
            downloaded = dest

            self.btn_apply_fix.setText("Uygulanıyor...")
            extracted_tmp = OnlineFixPatcher.apply_patch_from_archive(
                downloaded, str(self.app_id), target_path
            )
            used_online = True
        except OnlineFixNotFoundError as e:
            # Doğru fix bulunamadı: sessizce yerel şablona düşme, önce kullanıcıya sor.
            box = QMessageBox(self)
            box.setWindowTitle("Fix Bulunamadı")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(
                f"online-fix.me'de bu oyun için fix bulunamadı.\n\n{e}\n\n"
                "Yerel şablondan uygulamak ister misiniz?"
            )
            btn_yes = box.addButton("Evet, yerel şablonu uygula", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Hayır, iptal", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not btn_yes:
                return
            try:
                OnlineFixPatcher.apply_patch(self.app_id, target_path)
                QMessageBox.information(
                    self, "Yerel Şablon Uygulandı",
                    f"Fix bulunamadı; yerel şablon uygulandı.\n\nKlasör: {target_path}",
                )
            except Exception as local_err:
                QMessageBox.critical(
                    self, "Hata",
                    f"Yerel şablon uygulanamadı: {local_err}",
                )
                return
        except OnlineFixError as e:
            self.btn_apply_fix.setText("Yerel şablondan uygulanıyor...")
            try:
                OnlineFixPatcher.apply_patch(self.app_id, target_path)
                QMessageBox.warning(
                    self, "Kısmi",
                    f"İnternetten fix çekilemedi ({e}). Yerel şablondan uygulandı.",
                )
            except Exception as local_err:
                QMessageBox.critical(
                    self, "Hata",
                    f"İnternet fix'i: {e}\nYerel şablon: {local_err}",
                )
                return
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Fix uygulanırken hata oluştu:\n{e}")
            return
        finally:
            if downloaded and os.path.exists(downloaded):
                try:
                    os.remove(downloaded)
                except OSError:
                    pass
            if extracted_tmp and os.path.isdir(extracted_tmp):
                import shutil
                shutil.rmtree(extracted_tmp, ignore_errors=True)
            await client.close()

        if used_online:
            QMessageBox.information(
                self, "Başarılı",
                f"OnlineFix indirildi ve uygulandı, Steam yeniden başlatılıyor!\n\nKlasör: {target_path}",
            )

        subprocess.Popen(
            ["steam"], start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.btn_apply_fix.setEnabled(True)
        self.btn_apply_fix.setText("Apply Fix")
    def _uninstall_game(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        if getattr(self, '_installed_path', None):
            box = QMessageBox(self)
            box.setWindowTitle("Gelişmiş Kaldırma Seçenekleri")
            box.setText(f"{self.title} için neleri kaldırmak istiyorsunuz?")

            btn_both = box.addButton("Her İkisini Sil", QMessageBox.ButtonRole.AcceptRole)
            btn_game = box.addButton("Sadece Oyun Dosyalarını Sil", QMessageBox.ButtonRole.AcceptRole)
            btn_cancel = box.addButton("İptal", QMessageBox.ButtonRole.RejectRole)

            box.exec()

            if box.clickedButton() == btn_cancel:
                return

            remove_files = box.clickedButton() in (btn_both, btn_game)
            remove_lua = box.clickedButton() == btn_both
        else:
            confirm = QMessageBox.question(self, "Delete Lua", "Bu oyunu kütüphaneden (Lua) kaldırmak istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return
            remove_files = False
            remove_lua = True
        self.btn_uninstall.setEnabled(False)
        self.btn_uninstall.setText("Uninstalling...")

        def _run() -> None:
            try:
                from src.services.uninstall import uninstall_game
                summary = uninstall_game(self.app_id, remove_files=remove_files, remove_lua=remove_lua)
                QTimer.singleShot(0, lambda: self._on_uninstall_done(summary))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._on_uninstall_error(str(e)))

        import threading
        threading.Thread(target=_run, daemon=True).start()

    def _on_uninstall_done(self, summary: dict) -> None:
        from PySide6.QtWidgets import QMessageBox
        details = []
        if summary.get("files"):
            details.append("Game files deleted")
        if summary.get("acf"):
            details.append("appmanifest deleted")
        if summary.get("prefix"):
            details.append("Proton prefix deleted")
        if summary.get("depotcache"):
            details.append(f"{summary['depotcache']} depotcache manifest(s) deleted")
        if summary.get("config"):
            details.append("Library entry removed")
        QMessageBox.information(
            self,
            "Uninstall Complete",
            f"\"{self.title}\" has been uninstalled.\n\n" + ("\n".join(details) if details else "Nothing found to delete."),
        )
        self.uninstalled.emit(self.app_id)
        self.deleteLater()

    def _on_uninstall_error(self, error: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        self.btn_uninstall.setEnabled(True)
        self.btn_uninstall.setText("Uninstall")
        QMessageBox.warning(self, "Uninstall Failed", f"An error occurred:\n{error}")
