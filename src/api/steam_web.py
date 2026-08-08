import httpx
import asyncio

class SteamWebAPI:
    """Steam Web API üzerinden oyunların DLC bilgilerini çeken modül."""
    BASE_URL = "https://store.steampowered.com/api/appdetails"

    async def get_dlcs(self, app_id: int) -> list[dict]:
        async with httpx.AsyncClient() as client:
            try:
                # 1. Ana oyunun DLC listesini (ID'lerini) çek
                resp = await client.get(f"{self.BASE_URL}?appids={app_id}")
                if resp.status_code != 200:
                    return []
                
                data = resp.json()
                app_key = str(app_id)
                if not data.get(app_key, {}).get("success"):
                    return []
                
                dlc_ids = data[app_key]["data"].get("dlc", [])
                if not dlc_ids:
                    return []
                
                # 2. DLC ID'lerinin isimlerini eşzamanlı ama kontrollü (Rate Limit) çek
                results = []
                semaphore = asyncio.Semaphore(4) # Aynı anda en fazla 4 istek
                
                async def fetch_dlc_info(d_id: int):
                    async with semaphore:
                        name = f"DLC {d_id}" # Varsayılan isim
                        try:
                            # Hızlı yanıt için sadece temel bilgileri (filters=basic) çekiyoruz
                            d_resp = await client.get(f"{self.BASE_URL}?appids={d_id}&filters=basic", timeout=5.0)
                            if d_resp.status_code == 200:
                                d_data = d_resp.json()
                                d_key = str(d_id)
                                if d_data.get(d_key, {}).get("success"):
                                    name = d_data[d_key]["data"].get("name", name)
                        except Exception:
                            pass # Ağ hatası olursa varsayılan isme düşer
                            
                        results.append({
                            "app_id": d_id,
                            "name": name,
                            "image_url": f"https://cdn.akamai.steamstatic.com/steam/apps/{d_id}/header.jpg"
                        })
                
                # Tüm DLC'ler için görevleri oluştur ve bekle
                tasks = [fetch_dlc_info(d) for d in dlc_ids]
                await asyncio.gather(*tasks)
                
                # Listeyi ID'ye göre sırala ki arayüzde düzenli görünsün
                results.sort(key=lambda x: x["app_id"])
                return results
            except Exception as e:
                print(f"SteamWebAPI Hatası: {e}")
                return []
