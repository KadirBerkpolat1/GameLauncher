import asyncio
import httpx
from src.config.settings import SettingsManager

class DiscordScraperError(Exception):
    pass

class DiscordManifestScraper:
    """
    Discord üzerinden 'Self-Botting' yaparak SteamTools botu ile etkileşime giren modül.
    Kullanıcının girdiği Token ve ID'leri kullanarak /manifest slash komutunu tetikler.
    """
    def __init__(self):
        self.token = SettingsManager.get("discord_token", "").strip()
        self.guild_id = SettingsManager.get("discord_guild_id", "").strip()
        self.channel_id = SettingsManager.get("discord_channel_id", "").strip()
        self.bot_id = SettingsManager.get("discord_bot_id", "").strip()
        
        self.headers = {
            "Authorization": self.token, # User token, no 'Bot' prefix
            "Content-Type": "application/json"
        }
        
    async def fetch_manifest(self, app_id: int) -> bytes:
        if not all([self.token, self.guild_id, self.channel_id, self.bot_id]):
            raise DiscordScraperError("Eksik Discord Ayarları! Lütfen Ayarlar menüsünden Token, Sunucu ID, Kanal ID ve Bot ID'yi eksiksiz doldurun.")
            
        async with httpx.AsyncClient() as client:
            # 1. Komut ID'sini Dinamik Olarak Çek (Hardcode etmek risklidir)
            search_url = f"https://discord.com/api/v9/channels/{self.channel_id}/application-commands/search?query=manifest&type=1"
            resp = await client.get(search_url, headers=self.headers)
            if resp.status_code != 200:
                raise DiscordScraperError(f"Komut arama başarısız. Discord API Hatası: {resp.status_code}. (Token veya Kanal ID yanlış olabilir)")
            
            cmds = resp.json().get("application_commands", [])
            manifest_cmd = next((c for c in cmds if c["name"] == "manifest" and c["application_id"] == self.bot_id), None)
            
            if not manifest_cmd:
                raise DiscordScraperError(f"Bu kanalda {self.bot_id} botuna ait '/manifest' komutu bulunamadı.")
                
            cmd_id = manifest_cmd["id"]
            cmd_version = manifest_cmd["version"]
            
            # 2. Slash Komutunu Tetikle (Interaction POST)
            payload = {
                "type": 2,
                "application_id": self.bot_id,
                "guild_id": self.guild_id,
                "channel_id": self.channel_id,
                "session_id": "game_launcher_session", # Rastgele bir oturum ID'si
                "data": {
                    "version": cmd_version,
                    "id": cmd_id,
                    "name": "manifest",
                    "type": 1,
                    "options": [{"type": 4, "name": "appid", "value": app_id}]
                }
            }
            
            inter_resp = await client.post("https://discord.com/api/v9/interactions", headers=self.headers, json=payload)
            if inter_resp.status_code != 204:
                raise DiscordScraperError(f"Komut tetiklenemedi: {inter_resp.status_code} - {inter_resp.text}")
            
            # 3. Botun Yanıtını Bekle ve Dosyayı Çek (Polling)
            for _ in range(15): # 15 saniye boyunca bekle
                await asyncio.sleep(1)
                msg_resp = await client.get(f"https://discord.com/api/v9/channels/{self.channel_id}/messages?limit=10", headers=self.headers)
                if msg_resp.status_code == 200:
                    messages = msg_resp.json()
                    for msg in messages:
                        # Mesaj bottan mı geldi?
                        if msg.get("author", {}).get("id") == self.bot_id:
                            interaction = msg.get("interaction")
                            # Bizim tetiklediğimiz manifest komutunun yanıtı mı?
                            if interaction and interaction.get("name") == "manifest":
                                attachments = msg.get("attachments", [])
                                if attachments:
                                    # Ekteki dosyayı (Genelde ZIP veya LUA) indir
                                    file_url = attachments[0]["url"]
                                    file_resp = await client.get(file_url)
                                    return file_resp.content
                                elif "manifest" in msg.get("content", "").lower():
                                    return msg.get("content", "").encode('utf-8')
                                    
            raise DiscordScraperError("Bot komuta cevap vermedi (Zaman aşımı). Bot çevrimdışı veya yoğun olabilir.")