import os
import json
import sqlite3
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

# Se importará después de crear los archivos de configuración
# from .security_config import TelegramSecurityConfig, TelegramInputValidator, TelegramSecureLogger

class SecureMemoryManager:
    """
    Gestor de memoria securizado para el bot de Telegram.
    Incluye protección contra SQL injection, validación de entrada y logging seguro.
    """
    
    def __init__(self, db_path: str = "telegram_bot_memory_secure.db"):
        """Inicializa el gestor de memoria securizado."""
        self.db_path = db_path
        self.connection_timeout = 30
        self._init_db()
        print("SecureMemoryManager inicializado")
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones seguras a la base de datos."""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path, 
                timeout=self.connection_timeout,
                check_same_thread=False
            )
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except sqlite3.Error as e:
            print(f"Error de base de datos: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_db(self):
        """Inicializa la base de datos con constraints de seguridad."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de usuarios con constraints
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY CHECK(user_id > 0),
                username TEXT CHECK(length(username) <= 100),
                first_name TEXT CHECK(length(first_name) <= 100),
                last_name TEXT CHECK(length(last_name) <= 100),
                preferred_symbols TEXT CHECK(length(preferred_symbols) <= 1000),
                preferred_timeframes TEXT CHECK(length(preferred_timeframes) <= 500),
                analysis_style TEXT CHECK(analysis_style IN ('standard', 'detailed', 'brief')),
                custom_cryptos TEXT CHECK(length(custom_cryptos) <= 1000),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Tabla de mensajes con límites
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER CHECK(user_id > 0),
                role TEXT CHECK(role IN ('user', 'assistant')),
                content TEXT CHECK(length(content) <= 8000),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            ''')
            
            # Tabla de alertas con constraints
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER CHECK(user_id > 0),
                symbol TEXT CHECK(length(symbol) <= 20),
                condition_type TEXT CHECK(condition_type IN ('price_above', 'price_below', 'rsi_above', 'rsi_below', 'rsi_oversold', 'rsi_overbought', 'volume_high')),
                condition_value REAL CHECK(condition_value > 0 AND condition_value <= 1000000),
                timeframe TEXT CHECK(timeframe IN ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M')),
                is_active INTEGER CHECK(is_active IN (0, 1)) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                notification_sent INTEGER CHECK(notification_sent IN (0, 1)) DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
            ''')
            
            # Índices para rendimiento
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_timestamp ON messages(user_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, is_active)")
            
            conn.commit()
    
    def create_or_update_user(self, user_id: int, username: Optional[str] = None,
                            first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Crea o actualiza un usuario de forma segura."""
        if not isinstance(user_id, int) or user_id <= 0:
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                existing_user = cursor.fetchone()
                
                current_time = datetime.now().isoformat()
                
                if existing_user:
                    cursor.execute(
                        """UPDATE users SET username = COALESCE(?, username),
                           first_name = COALESCE(?, first_name),
                           last_name = COALESCE(?, last_name),
                           last_active = ? WHERE user_id = ?""",
                        (username, first_name, last_name, current_time, user_id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO users 
                        (user_id, username, first_name, last_name, preferred_symbols, preferred_timeframes, analysis_style, custom_cryptos)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, username, first_name, last_name, "[]", "[]", "standard", "[]")
                    )
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Error creando/actualizando usuario: {str(e)}")
            return False
    
    def add_message(self, user_id: int, role: str, content: str) -> bool:
        """Añade un mensaje al historial de forma segura."""
        if not isinstance(user_id, int) or user_id <= 0:
            return False
        
        if role not in ['user', 'assistant']:
            return False
        
        if not content or len(content) > 8000:
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar límite de historial por usuario (100 mensajes máx)
                cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,))
                message_count = cursor.fetchone()[0]
                
                if message_count >= 100:
                    # Eliminar mensajes más antiguos
                    cursor.execute(
                        """DELETE FROM messages WHERE user_id = ? AND id IN (
                           SELECT id FROM messages WHERE user_id = ? 
                           ORDER BY timestamp ASC LIMIT ?)""",
                        (user_id, user_id, message_count - 99)
                    )
                
                cursor.execute(
                    "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                    (user_id, role, content)
                )
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Error añadiendo mensaje: {str(e)}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información de un usuario de forma segura.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return None
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Query parametrizada para prevenir SQL injection
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user_data = cursor.fetchone()
                
                if not user_data:
                    return None
                
                columns = [
                    "user_id", "username", "first_name", "last_name", 
                    "preferred_symbols", "preferred_timeframes", "analysis_style",
                    "custom_cryptos", "created_at", "last_active"
                ]
                
                user = {columns[i]: user_data[i] for i in range(len(columns))}
                
                # Convertir strings JSON a listas de forma segura
                try:
                    user["preferred_symbols"] = json.loads(user["preferred_symbols"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    user["preferred_symbols"] = []
                
                try:
                    user["preferred_timeframes"] = json.loads(user["preferred_timeframes"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    user["preferred_timeframes"] = []
                
                try:
                    user["custom_cryptos"] = json.loads(user["custom_cryptos"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    user["custom_cryptos"] = []
                
                return user
                
        except sqlite3.Error as e:
            print(f"Error obteniendo usuario: {str(e)}")
            return None
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de conversación de forma segura.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return []
        
        # Validar límite
        limit = max(1, min(limit, 50))  # Entre 1 y 50
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT role, content, timestamp 
                    FROM messages 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    """,
                    (user_id, limit)
                )
                
                messages = cursor.fetchall()
                
                # Convertir a formato de diccionario
                result = []
                for msg in reversed(messages):  # Orden cronológico
                    result.append({
                        "role": msg[0],
                        "content": msg[1],
                        "timestamp": msg[2]
                    })
                
                return result
                
        except sqlite3.Error as e:
            print(f"Error obteniendo historial: {str(e)}")
            return []
    
    def create_alert(
        self, 
        user_id: int, 
        symbol: str, 
        condition_type: str, 
        condition_value, 
        timeframe: str = "1h"
    ) -> Optional[int]:
        """
        Crea una alerta de forma segura.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return None
        
        # Validar entradas
        if not isinstance(symbol, str) or len(symbol) > 20:
            print(f"Símbolo inválido en alerta: {symbol}")
            return None
        
        if not isinstance(timeframe, str) or timeframe not in ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']:
            print(f"Timeframe inválido en alerta: {timeframe}")
            return None
        
        # Actualizar tipos de condición para incluir los nuevos
        valid_conditions = ['price_above', 'price_below', 'rsi_above', 'rsi_below', 'rsi_oversold', 'rsi_overbought', 'volume_high']
        if not isinstance(condition_type, str) or condition_type not in valid_conditions:
            print(f"Tipo de condición inválido: {condition_type}")
            return None
        
        # Convertir condition_value a float si es string
        try:
            if isinstance(condition_value, str):
                if condition_value == "auto":
                    # Para condiciones automáticas (RSI, volumen), usar valor simbólico
                    condition_value = 1.0
                else:
                    condition_value = float(condition_value)
            
            if not isinstance(condition_value, (int, float)) or condition_value <= 0 or condition_value > 1000000:
                print(f"Valor de condición inválido: {condition_value}")
                return None
        except (ValueError, TypeError):
            print(f"Error convirtiendo valor de condición: {condition_value}")
            return None
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar límite de alertas por usuario
                cursor.execute(
                    "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND is_active = 1",
                    (user_id,)
                )
                alert_count = cursor.fetchone()[0]
                
                if alert_count >= 10:
                    print("Usuario excedió límite de alertas")
                    return None
                
                # Crear alerta
                cursor.execute(
                    """
                    INSERT INTO alerts (user_id, symbol, condition_type, condition_value, timeframe)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, symbol.upper(), condition_type, condition_value, timeframe)
                )
                
                alert_id = cursor.lastrowid
                conn.commit()
                
                print(f"Alerta creada: {symbol} {condition_type} {condition_value}")
                return alert_id
                
        except sqlite3.Error as e:
            print(f"Error creando alerta: {str(e)}")
            return None
    
    def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene las alertas de un usuario de forma segura.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return []
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if active_only:
                    cursor.execute(
                        """
                        SELECT id, symbol, condition_type, condition_value, timeframe, created_at
                        FROM alerts 
                        WHERE user_id = ? AND is_active = 1
                        ORDER BY created_at DESC
                        """,
                        (user_id,)
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, symbol, condition_type, condition_value, timeframe, created_at, is_active
                        FROM alerts 
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        """,
                        (user_id,)
                    )
                
                alerts_data = cursor.fetchall()
                
                alerts = []
                for alert in alerts_data:
                    alert_dict = {
                        "id": alert[0],
                        "symbol": alert[1],
                        "condition_type": alert[2],
                        "condition_value": alert[3],
                        "timeframe": alert[4],
                        "created_at": alert[5]
                    }
                    
                    if not active_only:
                        alert_dict["is_active"] = bool(alert[6])
                    
                    alerts.append(alert_dict)
                
                return alerts
                
        except sqlite3.Error as e:
            print(f"Error obteniendo alertas: {str(e)}")
            return []
    
    def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """
        Elimina una alerta de forma segura (verificando propiedad).
        """
        if not isinstance(user_id, int) or user_id <= 0 or not isinstance(alert_id, int) or alert_id <= 0:
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar que la alerta pertenece al usuario
                cursor.execute(
                    "SELECT user_id FROM alerts WHERE id = ?",
                    (alert_id,)
                )
                result = cursor.fetchone()
                
                if not result or result[0] != user_id:
                    print(f"Intento de eliminar alerta ajena: {alert_id}")
                    return False
                
                # Eliminar alerta
                cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
                deleted = cursor.rowcount > 0
                
                conn.commit()
                
                if deleted:
                    print(f"Alerta eliminada: {alert_id}")
                
                return deleted
                
        except sqlite3.Error as e:
            print(f"Error eliminando alerta: {str(e)}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """
        Limpia datos antiguos para mantener la base de datos eficiente.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Eliminar mensajes antiguos
                cursor.execute(
                    "DELETE FROM messages WHERE timestamp < datetime('now', '-{} days')".format(days_to_keep)
                )
                messages_deleted = cursor.rowcount
                
                # Eliminar análisis antiguos
                cursor.execute(
                    "DELETE FROM analyses WHERE timestamp < datetime('now', '-{} days')".format(days_to_keep)
                )
                analyses_deleted = cursor.rowcount
                
                conn.commit()
                
                print(
                    f"Limpieza completada: {messages_deleted} mensajes, {analyses_deleted} análisis eliminados"
                )
                
        except sqlite3.Error as e:
            print(f"Error en limpieza de datos: {str(e)}")
    
    def get_user_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene la configuración personalizada del usuario."""
        if not isinstance(user_id, int) or user_id <= 0:
            return None
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT custom_cryptos, preferred_symbols, preferred_timeframes FROM users WHERE user_id = ?", 
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                custom_cryptos, preferred_symbols, preferred_timeframes = result
                
                config = {}
                
                # Parsear custom_cryptos como favorite_cryptos
                try:
                    if custom_cryptos:
                        config['favorite_cryptos'] = json.loads(custom_cryptos)
                    else:
                        config['favorite_cryptos'] = []
                except json.JSONDecodeError:
                    config['favorite_cryptos'] = []
                
                # Parsear timeframes favoritos
                try:
                    if preferred_timeframes:
                        config['favorite_timeframes'] = json.loads(preferred_timeframes)
                    else:
                        config['favorite_timeframes'] = []
                except json.JSONDecodeError:
                    config['favorite_timeframes'] = []
                
                return config
                
        except sqlite3.Error as e:
            print(f"Error obteniendo configuración de usuario: {str(e)}")
            return None
    
    def set_user_config(self, user_id: int, config: Dict[str, Any]) -> bool:
        """Establece la configuración personalizada del usuario."""
        if not isinstance(user_id, int) or user_id <= 0:
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Preparar datos para guardar
                custom_cryptos = json.dumps(config.get('favorite_cryptos', []))
                preferred_timeframes = json.dumps(config.get('favorite_timeframes', []))
                
                # Validar tamaños
                if len(custom_cryptos) > 1000 or len(preferred_timeframes) > 500:
                    return False
                
                cursor.execute(
                    """UPDATE users SET 
                       custom_cryptos = ?,
                       preferred_timeframes = ?,
                       last_active = CURRENT_TIMESTAMP
                       WHERE user_id = ?""",
                    (custom_cryptos, preferred_timeframes, user_id)
                )
                
                if cursor.rowcount == 0:
                    # Usuario no existe, crearlo
                    cursor.execute(
                        """INSERT INTO users 
                        (user_id, username, first_name, last_name, preferred_symbols, preferred_timeframes, analysis_style, custom_cryptos)
                        VALUES (?, NULL, NULL, NULL, '[]', ?, 'standard', ?)""",
                        (user_id, preferred_timeframes, custom_cryptos)
                    )
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Error estableciendo configuración de usuario: {str(e)}")
            return False

    def get_all_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las alertas activas del sistema para el servicio de monitoreo.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, user_id, symbol, condition_type, condition_value, timeframe, created_at, notification_sent
                    FROM alerts 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                    """
                )
                
                alerts_data = cursor.fetchall()
                
                alerts = []
                for alert in alerts_data:
                    alert_dict = {
                        "id": alert[0],
                        "user_id": alert[1],
                        "symbol": alert[2],
                        "condition_type": alert[3],
                        "condition_value": alert[4],
                        "timeframe": alert[5],
                        "created_at": alert[6],
                        "notification_sent": bool(alert[7]) if alert[7] is not None else False
                    }
                    alerts.append(alert_dict)
                
                return alerts
                
        except sqlite3.Error as e:
            print(f"Error obteniendo todas las alertas activas: {str(e)}")
            return []

    def update_alert(self, alert_id: int, **kwargs) -> bool:
        """
        Actualiza campos de una alerta específica.
        """
        if not isinstance(alert_id, int) or alert_id <= 0:
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Construir query dinámico basado en kwargs
                fields = []
                values = []
                
                for field, value in kwargs.items():
                    if field in ['notification_sent', 'is_active']:
                        fields.append(f"{field} = ?")
                        values.append(int(value) if isinstance(value, bool) else value)
                
                if not fields:
                    return False
                
                values.append(alert_id)
                query = f"UPDATE alerts SET {', '.join(fields)} WHERE id = ?"
                
                cursor.execute(query, values)
                updated = cursor.rowcount > 0
                
                conn.commit()
                return updated
                
        except sqlite3.Error as e:
            print(f"Error actualizando alerta: {str(e)}")
            return False