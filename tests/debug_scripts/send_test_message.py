#!/usr/bin/env python3
"""
Script para enviar un mensaje de prueba al bot
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def send_test_message():
    """Envía un mensaje de prueba al bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("❌ TELEGRAM_TOKEN no configurado")
        return
    
    # Obtener el chat_id del usuario (necesitas enviar un mensaje al bot primero)
    print("🔍 Obteniendo actualizaciones...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"https://api.telegram.org/bot{token}/getUpdates?limit=10")
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    updates = data['result']
                    if updates:
                        # Tomar el último chat_id
                        last_update = updates[-1]
                        if 'message' in last_update:
                            chat_id = last_update['message']['chat']['id']
                            user_name = last_update['message']['from'].get('first_name', 'Usuario')
                            print(f"✅ Chat ID encontrado: {chat_id} ({user_name})")
                            
                            # Enviar mensaje de prueba
                            test_message = "🧪 Mensaje de prueba - ¿Me recibes?"
                            response = await client.post(
                                f"https://api.telegram.org/bot{token}/sendMessage",
                                json={
                                    "chat_id": chat_id,
                                    "text": test_message
                                }
                            )
                            
                            if response.status_code == 200:
                                print("✅ Mensaje de prueba enviado correctamente")
                                print("📱 Revisa Telegram para ver si el bot responde")
                            else:
                                print(f"❌ Error enviando mensaje: {response.status_code}")
                                print(response.text)
                        else:
                            print("❌ No se encontró un mensaje válido en las actualizaciones")
                    else:
                        print("❌ No hay actualizaciones. Envía un mensaje al bot primero.")
                        print("📱 Ve a Telegram, busca @Master_IA_bot y envía cualquier mensaje")
                else:
                    print(f"❌ Error en getUpdates: {data}")
            else:
                print(f"❌ Error HTTP: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(send_test_message()) 