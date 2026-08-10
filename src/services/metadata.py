import asyncio
import httpx
import logging

class MetadataFetcher:
    """Fetches depot metadata and DLC names from Steam APIs."""
    
    @staticmethod
    async def fetch_depot_metadata(app_id: int, hubcap_depots: list) -> dict:
        """
        Fetches depot metadata for the given app_id and filters the hubcap_depots.
        Returns a dict mapping dlc_appid (or 'base') to a dict containing:
        - name: str
        - depots: list of depot_ids
        - size: (optional, based on maxsize)
        """
        metadata = {
            "base_common": {"name": "Temel Oyun (Ortak Dosyalar)", "depots": [], "size": 0, "required": True},
            "base_windows": {"name": "Windows Dosyaları", "depots": [], "size": 0, "required": False},
            "base_linux": {"name": "Linux Dosyaları", "depots": [], "size": 0, "required": False},
            "dlcs": {}
        }
        
        steam_depots = {}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.steamcmd.net/v1/info/{app_id}", timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get(str(app_id), {})
                    steam_depots = data.get("depots", {})
        except Exception as e:
            logging.error(f"Failed to fetch depot metadata from steamcmd.net: {e}")
            # Fallback: put everything in base_common
            metadata["base_common"]["depots"] = hubcap_depots.copy()
            return metadata
            
        dlc_appids = set()
        
        for depot_id in hubcap_depots:
            depot_str = str(depot_id)
            d_info = steam_depots.get(depot_str, {})
            
            # Skip non-dict info if any malformed data exists
            if not isinstance(d_info, dict):
                metadata["base_common"]["depots"].append(depot_id)
                continue
                
            # Filter OS
            config = d_info.get("config", {})
            oslist = config.get("oslist", "")
            if oslist:
                # If it's specifically for macos/osx and doesn't contain windows or linux, skip it
                if ("macos" in oslist or "osx" in oslist) and "windows" not in oslist and "linux" not in oslist:
                    continue
                    
            dlc_appid = d_info.get("dlcappid")
            maxsize = int(d_info.get("maxsize", 0))
            
            if dlc_appid:
                dlc_appid_str = str(dlc_appid)
                dlc_appids.add(dlc_appid_str)
                if dlc_appid_str not in metadata["dlcs"]:
                    metadata["dlcs"][dlc_appid_str] = {
                        "name": f"DLC {dlc_appid_str}",
                        "depots": [],
                        "size": 0
                    }
                metadata["dlcs"][dlc_appid_str]["depots"].append(depot_id)
                metadata["dlcs"][dlc_appid_str]["size"] += maxsize
            else:
                if oslist and "windows" in oslist.lower():
                    metadata["base_windows"]["depots"].append(depot_id)
                    metadata["base_windows"]["size"] += maxsize
                elif oslist and "linux" in oslist.lower():
                    metadata["base_linux"]["depots"].append(depot_id)
                    metadata["base_linux"]["size"] += maxsize
                else:
                    metadata["base_common"]["depots"].append(depot_id)
                    metadata["base_common"]["size"] += maxsize

        # Resolve DLC names concurrently
        if dlc_appids:
            sem = asyncio.Semaphore(5)
            
            async def fetch_dlc_info(client, dlc_id):
                async with sem:
                    try:
                        resp = await client.get(f"https://store.steampowered.com/api/appdetails?appids={dlc_id}", timeout=5.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data and data.get(dlc_id, {}).get("success"):
                                app_data = data[dlc_id]["data"]
                                return dlc_id, app_data.get("name"), app_data.get("header_image")
                    except Exception as e:
                        logging.error(f"Error fetching DLC info for {dlc_id}: {e}")
                    return dlc_id, None, None

            async with httpx.AsyncClient() as client:
                tasks = [fetch_dlc_info(client, dlc_id) for dlc_id in dlc_appids]
                results = await asyncio.gather(*tasks)
                
                for dlc_id, name, image in results:
                    if name:
                        metadata["dlcs"][dlc_id]["name"] = name
                    if image:
                        metadata["dlcs"][dlc_id]["image"] = image
                        
        return metadata
