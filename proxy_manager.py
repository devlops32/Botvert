import random
from typing import Optional, List
import aiohttp
from config import PROXY_FILE

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.load_proxies()
    
    def load_proxies(self):
        """Загрузка прокси из файла"""
        try:
            with open(PROXY_FILE, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(self.proxies)} proxies")
        except FileNotFoundError:
            print(f"Proxy file {PROXY_FILE} not found")
            self.proxies = []
    
    def get_proxy(self) -> Optional[str]:
        """Получение случайного прокси"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_proxy_dict(self) -> Optional[dict]:
        """Получение прокси в формате для aiohttp"""
        proxy = self.get_proxy()
        if not proxy:
            return None
        
        # Формат: user:pass@host:port
        if '@' in proxy:
            auth, host = proxy.split('@')
            user, password = auth.split(':')
            proxy_url = f"http://{host}"
            return {
                'proxy': proxy_url,
                'proxy_auth': aiohttp.BasicAuth(user, password)
            }
        else:
            return {'proxy': f"http://{proxy}"}
    
    def create_session(self) -> aiohttp.ClientSession:
        """Создание сессии с прокси"""
        proxy_config = self.get_proxy_dict()
        if proxy_config:
            return aiohttp.ClientSession(
                proxy=proxy_config.get('proxy'),
                proxy_auth=proxy_config.get('proxy_auth')
            )
        return aiohttp.ClientSession()

# Глобальный экземпляр
proxy_manager = ProxyManager()