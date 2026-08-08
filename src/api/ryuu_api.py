import httpx
from src.config.settings import SettingsManager

class RyuuAPIError(Exception):
    pass

class RyuuClient:
    """
    Ryuu API üzerinden Steam manifest dosyalarını ve decryption key'lerini barındıran
    ZIP dosyasını indirmek için kullanılan istemci.
    """
    BASE_URL = "https://generator.ryuu.lol/api"

    def __init__(self):
        self.api_key = SettingsManager.get("ryuu_api_key", "").strip()

    async def get_app_manifest_zip(self, app_id: int) -> bytes:
        if not self.api_key:
            raise RyuuAPIError("Ryuu API anahtarı eksik! Lütfen Ayarlar'dan 'X-Auth-Key' bilginizi girin.")

        headers = {
            "X-Auth-Key": self.api_key,
            "User-Agent": "GameLauncher/1.0"
        }

        # Sadece manifest dosyalarını ve lua (key) dosyasını içeren ZIP'i talep et
        url = f"{self.BASE_URL}/download/{app_id}?file_type=manifest"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=20.0)

                if response.status_code == 401 or response.status_code == 403:
                    raise RyuuAPIError("Geçersiz Ryuu API Anahtarı! (Yetkisiz Erişim)")
                elif response.status_code == 404:
                    raise RyuuAPIError(f"Oyun bulunamadı (AppID: {app_id}). Ryuu veritabanında mevcut değil.")
                elif response.status_code == 429:
                    raise RyuuAPIError("Ryuu API limitine takıldınız. Lütfen biraz bekleyin.")

                response.raise_for_status()
                return response.content

            except httpx.RequestError as e:
                raise RyuuAPIError(f"Ryuu sunucusuna bağlanırken ağ hatası oluştu: {e}")
            except httpx.HTTPStatusError as e:
                raise RyuuAPIError(f"Ryuu API Hatası ({e.response.status_code}): Beklenmeyen bir sunucu hatası.")

# Kolay erişim için global nesne
ryuu_api = RyuuClient()