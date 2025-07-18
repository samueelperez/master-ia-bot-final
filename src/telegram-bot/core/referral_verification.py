"""
Sistema de verificación de referidos para exchanges.
Soporta: Bitget, Blofin, Bitunix, BingX
"""

import os
import hmac
import hashlib
import time
import json
import logging
import base64
from typing import Dict, Optional, Tuple, Any
import httpx
from dataclasses import dataclass
from datetime import datetime

# Configuración del logger
logger = logging.getLogger(__name__)

@dataclass
class ExchangeConfig:
    """Configuración para cada exchange."""
    name: str
    api_key: str
    api_secret: str
    base_url: str
    enabled: bool = False

class ReferralVerifier:
    """Verificador de referidos para múltiples exchanges."""
    
    def __init__(self):
        self.exchanges = self._load_exchange_configs()
        self.timeout = 30
    
    def _load_exchange_configs(self) -> Dict[str, ExchangeConfig]:
        """Carga configuraciones de exchanges desde variables de entorno."""
        configs = {}
        
        # Bitget
        bitget_key = os.getenv("BITGET_API_KEY", "")
        bitget_secret = os.getenv("BITGET_API_SECRET", "")
        if bitget_key and bitget_secret and "tu_api_key" not in bitget_key:
            configs["bitget"] = ExchangeConfig(
                name="Bitget",
                api_key=bitget_key,
                api_secret=bitget_secret,
                base_url="https://api.bitget.com",
                enabled=True
            )
        
        # Blofin
        blofin_key = os.getenv("BLOFIN_API_KEY", "")
        blofin_secret = os.getenv("BLOFIN_API_SECRET", "")
        if blofin_key and blofin_secret and "tu_api_key" not in blofin_key:
            configs["blofin"] = ExchangeConfig(
                name="Blofin",
                api_key=blofin_key,
                api_secret=blofin_secret,
                base_url="https://openapi.blofin.com",
                enabled=True
            )
        
        # Bitunix
        bitunix_key = os.getenv("BITUNIX_API_KEY", "")
        bitunix_secret = os.getenv("BITUNIX_API_SECRET", "")
        if bitunix_key and bitunix_secret and "tu_api_key" not in bitunix_key:
            configs["bitunix"] = ExchangeConfig(
                name="Bitunix",
                api_key=bitunix_key,
                api_secret=bitunix_secret,
                base_url="https://partners.bitunix.com",
                enabled=True
            )
        
        # BingX
        bingx_key = os.getenv("BINGX_API_KEY", "")
        bingx_secret = os.getenv("BINGX_API_SECRET", "")
        if bingx_key and bingx_secret and "tu_api_key" not in bingx_key:
            configs["bingx"] = ExchangeConfig(
                name="BingX",
                api_key=bingx_key,
                api_secret=bingx_secret,
                base_url="https://open-api.bingx.com",
                enabled=True
            )
        
        return configs
    
    def get_enabled_exchanges(self) -> list[str]:
        """Retorna lista de exchanges habilitados."""
        return [name for name, config in self.exchanges.items() if config.enabled]
    
    async def verify_referral(self, uid: str) -> Tuple[bool, str, Optional[str]]:
        """
        Verifica si un UID es referido en algún exchange configurado.
        
        Args:
            uid: User ID a verificar
            
        Returns:
            Tuple[bool, str, Optional[str]]: (es_referido, mensaje, exchange_encontrado)
        """
        if not uid or not uid.strip():
            return False, "UID no puede estar vacío", None
        
        if not self.exchanges:
            return False, "No hay exchanges configurados para verificación", None
        
        # Intentar verificar en cada exchange habilitado
        results = []
        
        for exchange_name, config in self.exchanges.items():
            if not config.enabled:
                continue
                
            try:
                logger.info(f"Verificando UID {uid} en {config.name}...")
                
                is_referred = await self._verify_in_exchange(uid, exchange_name, config)
                
                if is_referred:
                    logger.info(f"✅ UID {uid} verificado como referido en {config.name}")
                    return True, f"Referido verificado en {config.name}", exchange_name
                else:
                    results.append(f"{config.name}: No encontrado")
                    
            except Exception as e:
                error_msg = f"{config.name}: Error - {str(e)[:100]}"
                results.append(error_msg)
                logger.error(f"Error verificando en {config.name}: {e}")
        
        # Si llegamos aquí, no se encontró en ningún exchange
        return False, f"UID no encontrado como referido en: {', '.join(results)}", None
    
    async def _verify_in_exchange(self, uid: str, exchange_name: str, config: ExchangeConfig) -> bool:
        """Verifica un UID en un exchange específico."""
        if exchange_name == "bitget":
            return await self._verify_bitget(uid, config)
        elif exchange_name == "blofin":
            return await self._verify_blofin(uid, config)
        elif exchange_name == "bitunix":
            return await self._verify_bitunix(uid, config)
        elif exchange_name == "bingx":
            return await self._verify_bingx(uid, config)
        else:
            raise ValueError(f"Exchange no soportado: {exchange_name}")
    
    async def _verify_bitget(self, uid: str, config: ExchangeConfig) -> bool:
        """Verificar en Bitget."""
        timestamp = str(int(time.time() * 1000))
        method = "POST"
        request_path = "/api/broker/v1/agent/customerList"
        
        body = {"uid": uid}
        body_str = json.dumps(body)
        
        # Crear firma según especificación de Bitget
        prehash = timestamp + method + request_path + body_str
        signature = hmac.new(
            config.api_secret.encode('utf-8'),
            prehash.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_base64 = base64.b64encode(signature).decode('utf-8')
        
        headers = {
            "ACCESS-KEY": config.api_key,
            "ACCESS-SIGN": signature_base64,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": os.getenv("BITGET_PASSPHRASE", ""),
            "Content-Type": "application/json"
        }
        
        url = config.base_url + request_path
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=body)
            
            if response.status_code == 200:
                data = response.json()
                # Verificar si el UID está en la lista de referidos
                return self._check_bitget_response(data, uid)
            else:
                logger.error(f"Error Bitget: {response.status_code} - {response.text}")
                return False
    
    async def _verify_blofin(self, uid: str, config: ExchangeConfig) -> bool:
        """Verificar en Blofin."""
        query = f"?uid={uid}"
        path = "/api/v1/affiliate/invitees" + query
        method = "GET"
        timestamp = str(int(time.time() * 1000))
        nonce = uid  # Usar UID como nonce
        body = ""
        
        # Crear firma según especificación de Blofin
        prehash = path + method + timestamp + nonce + body
        hex_signature = hmac.new(
            config.api_secret.encode('utf-8'),
            prehash.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Convertir hex a bytes UTF-8 y luego a base64
        hex_as_bytes = hex_signature.encode('utf-8')
        signature = base64.b64encode(hex_as_bytes).decode('utf-8')
        
        headers = {
            "ACCESS-KEY": config.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-NONCE": nonce,
            "Content-Type": "application/json"
        }
        
        url = config.base_url + path
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return self._check_blofin_response(data, uid)
            else:
                logger.error(f"Error Blofin: {response.status_code} - {response.text}")
                return False
    
    async def _verify_bitunix(self, uid: str, config: ExchangeConfig) -> bool:
        """Verificar en Bitunix."""
        timestamp = int(time.time())
        
        data = {
            "timestamp": timestamp,
            "account": uid
        }
        
        # Ordenar parámetros según especificación de Bitunix
        def get_parameter_type(s):
            if s[0].isdigit():
                return 1
            elif s[0].islower():
                return 2
            return 3
        
        def str_to_ascii_sum(s):
            return sum(ord(char) for char in s)
        
        sorted_keys = sorted(data.keys(), key=lambda x: (get_parameter_type(x), str_to_ascii_sum(x)))
        sorted_params = {key: data[key] for key in sorted_keys}
        
        # Generar firma
        concatenated_string = ''.join(str(value) for value in sorted_params.values())
        signature = hashlib.sha1((concatenated_string + config.api_secret).encode()).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "apiKey": config.api_key,
            "signature": signature
        }
        
        # Construir query string
        query_parts = [f"{key}={value}" for key, value in sorted_params.items()]
        query_string = "&".join(query_parts)
        
        url = f"{config.base_url}/partner/api/v2/openapi/userList?{query_string}"
        
        async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return self._check_bitunix_response(data, uid)
            else:
                logger.error(f"Error Bitunix: {response.status_code} - {response.text}")
                return False
    
    async def _verify_bingx(self, uid: str, config: ExchangeConfig) -> bool:
        """Verificar en BingX."""
        timestamp = int(time.time() * 1000)
        params = f"uid={uid}&timestamp={timestamp}"
        
        signature = hmac.new(
            config.api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-BX-APIKEY": config.api_key
        }
        
        url = f"{config.base_url}/openApi/agent/v1/account/inviteRelationCheck?{params}&signature={signature}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return self._check_bingx_response(data, uid)
            else:
                logger.error(f"Error BingX: {response.status_code} - {response.text}")
                return False
    
    def _check_bitget_response(self, data: dict, uid: str) -> bool:
        """Verifica respuesta de Bitget."""
        try:
            if data.get("code") == "00000" and data.get("data"):
                customers = data["data"]
                return any(customer.get("uid") == uid for customer in customers)
            return False
        except Exception as e:
            logger.error(f"Error procesando respuesta Bitget: {e}")
            return False
    
    def _check_blofin_response(self, data: dict, uid: str) -> bool:
        """Verifica respuesta de Blofin."""
        try:
            if data.get("code") == "0" and data.get("data"):
                invitees = data["data"]
                return any(invitee.get("uid") == uid for invitee in invitees)
            return False
        except Exception as e:
            logger.error(f"Error procesando respuesta Blofin: {e}")
            return False
    
    def _check_bitunix_response(self, data: dict, uid: str) -> bool:
        """Verifica respuesta de Bitunix."""
        try:
            if data.get("code") == 200 and data.get("data"):
                users = data["data"]
                return any(user.get("account") == uid for user in users)
            return False
        except Exception as e:
            logger.error(f"Error procesando respuesta Bitunix: {e}")
            return False
    
    def _check_bingx_response(self, data: dict, uid: str) -> bool:
        """Verifica respuesta de BingX."""
        try:
            if data.get("code") == 0:
                # BingX retorna success cuando encuentra el referido
                return data.get("data", {}).get("isInvited", False)
            return False
        except Exception as e:
            logger.error(f"Error procesando respuesta BingX: {e}")
            return False

# Instancia global del verificador
referral_verifier = ReferralVerifier() 