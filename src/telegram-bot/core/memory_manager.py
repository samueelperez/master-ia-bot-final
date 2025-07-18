import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

class MemoryManager:
    """
    Gestor de memoria para el bot de Telegram.
    Proporciona funcionalidades para almacenar y recuperar:
    - Memoria a corto plazo: historial de conversaciones recientes
    - Memoria a largo plazo: preferencias de usuario y patrones de uso
    """
    
    def __init__(self, db_path: str = "bot_memory.db"):
        """
        Inicializa el gestor de memoria.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializa la base de datos si no existe."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            preferred_symbols TEXT,
            preferred_timeframes TEXT,
            analysis_style TEXT,
            custom_cryptos TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Verificar si la columna custom_cryptos existe, y añadirla si no
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "custom_cryptos" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_cryptos TEXT")
        
        # Tabla de mensajes (historial de conversaciones)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Tabla de análisis realizados
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            timeframe TEXT,
            prompt TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Tabla de alertas
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            condition_type TEXT,
            condition_value REAL,
            timeframe TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked TIMESTAMP,
            notification_sent INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            
        Returns:
            Diccionario con la información del usuario o None si no existe
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        conn.close()
        
        if not user_data:
            return None
        
        columns = [
            "user_id", "username", "first_name", "last_name", 
            "preferred_symbols", "preferred_timeframes", "analysis_style",
            "created_at", "last_active"
        ]
        
        user = {columns[i]: user_data[i] for i in range(len(columns))}
        
        # Convertir strings JSON a listas
        if user["preferred_symbols"]:
            user["preferred_symbols"] = json.loads(user["preferred_symbols"])
        else:
            user["preferred_symbols"] = []
            
        if user["preferred_timeframes"]:
            user["preferred_timeframes"] = json.loads(user["preferred_timeframes"])
        else:
            user["preferred_timeframes"] = []
        
        return user
    
    def create_or_update_user(
        self, 
        user_id: int, 
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> None:
        """
        Crea o actualiza un usuario en la base de datos.
        
        Args:
            user_id: ID del usuario de Telegram
            username: Nombre de usuario de Telegram
            first_name: Nombre del usuario
            last_name: Apellido del usuario
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verificar si el usuario ya existe
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()
        
        current_time = datetime.now().isoformat()
        
        if existing_user:
            # Actualizar usuario existente
            cursor.execute(
                """
                UPDATE users 
                SET username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name),
                    last_name = COALESCE(?, last_name),
                    last_active = ?
                WHERE user_id = ?
                """,
                (username, first_name, last_name, current_time, user_id)
            )
        else:
            # Crear nuevo usuario
            cursor.execute(
                """
                INSERT INTO users 
                (user_id, username, first_name, last_name, preferred_symbols, preferred_timeframes, analysis_style, custom_cryptos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, first_name, last_name, "[]", "[]", "standard", "[]")
            )
        
        conn.commit()
        conn.close()
    
    def update_user_preferences(
        self,
        user_id: int,
        preferred_symbols: Optional[List[str]] = None,
        preferred_timeframes: Optional[List[str]] = None,
        analysis_style: Optional[str] = None
    ) -> None:
        """
        Actualiza las preferencias de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            preferred_symbols: Lista de símbolos preferidos
            preferred_timeframes: Lista de timeframes preferidos
            analysis_style: Estilo de análisis preferido
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtener preferencias actuales
        user = self.get_user(user_id)
        if not user:
            self.create_or_update_user(user_id)
            user = {
                "preferred_symbols": [],
                "preferred_timeframes": [],
                "analysis_style": "standard"
            }
        
        # Actualizar con nuevos valores o mantener los actuales
        symbols = json.dumps(preferred_symbols if preferred_symbols is not None else user["preferred_symbols"])
        timeframes = json.dumps(preferred_timeframes if preferred_timeframes is not None else user["preferred_timeframes"])
        style = analysis_style if analysis_style is not None else user["analysis_style"]
        
        cursor.execute(
            """
            UPDATE users 
            SET preferred_symbols = ?,
                preferred_timeframes = ?,
                analysis_style = ?,
                last_active = ?
            WHERE user_id = ?
            """,
            (symbols, timeframes, style, datetime.now().isoformat(), user_id)
        )
        
        conn.commit()
        conn.close()
    
    def add_message(self, user_id: int, role: str, content: str) -> None:
        """
        Añade un mensaje al historial de conversación.
        
        Args:
            user_id: ID del usuario de Telegram
            role: Rol del mensaje ('user' o 'assistant')
            content: Contenido del mensaje
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Asegurarse de que el usuario existe
        user = self.get_user(user_id)
        if not user:
            self.create_or_update_user(user_id)
        
        # Añadir mensaje
        cursor.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        
        # Actualizar timestamp de última actividad
        cursor.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de conversación reciente de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            limit: Número máximo de mensajes a recuperar
            
        Returns:
            Lista de mensajes ordenados cronológicamente
        """
        conn = sqlite3.connect(self.db_path)
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
        conn.close()
        
        # Convertir a formato de lista de diccionarios y ordenar cronológicamente
        result = [
            {"role": msg[0], "content": msg[1], "timestamp": msg[2]}
            for msg in messages
        ]
        
        # Invertir para tener orden cronológico (más antiguos primero)
        result.reverse()
        
        return result
    
    def add_analysis(self, user_id: int, symbol: str, timeframe: str, prompt: str, response: str) -> None:
        """
        Registra un análisis realizado.
        
        Args:
            user_id: ID del usuario de Telegram
            symbol: Símbolo de la criptomoneda analizada
            timeframe: Timeframe del análisis
            prompt: Consulta del usuario
            response: Respuesta generada
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Asegurarse de que el usuario existe
        user = self.get_user(user_id)
        if not user:
            self.create_or_update_user(user_id)
        
        # Añadir análisis
        cursor.execute(
            """
            INSERT INTO analyses (user_id, symbol, timeframe, prompt, response)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, symbol, timeframe, prompt, response)
        )
        
        # Actualizar timestamp de última actividad
        cursor.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        
        conn.commit()
        conn.close()
        
        # Actualizar preferencias basadas en el uso
        self._update_preferences_from_usage(user_id, symbol, timeframe)
    
    def _update_preferences_from_usage(self, user_id: int, symbol: str, timeframe: str) -> None:
        """
        Actualiza automáticamente las preferencias del usuario basadas en su uso.
        
        Args:
            user_id: ID del usuario de Telegram
            symbol: Símbolo de la criptomoneda analizada
            timeframe: Timeframe del análisis
        """
        user = self.get_user(user_id)
        if not user:
            return
        
        # Actualizar símbolos preferidos
        preferred_symbols = user["preferred_symbols"]
        if symbol not in preferred_symbols:
            preferred_symbols.append(symbol)
            # Mantener solo los 5 más recientes
            if len(preferred_symbols) > 5:
                preferred_symbols.pop(0)
        
        # Actualizar timeframes preferidos
        preferred_timeframes = user["preferred_timeframes"]
        if timeframe not in preferred_timeframes:
            preferred_timeframes.append(timeframe)
            # Mantener solo los 3 más recientes
            if len(preferred_timeframes) > 3:
                preferred_timeframes.pop(0)
        
        # Guardar preferencias actualizadas
        self.update_user_preferences(
            user_id,
            preferred_symbols=preferred_symbols,
            preferred_timeframes=preferred_timeframes
        )
    
    def get_recent_analyses(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Obtiene los análisis recientes de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            limit: Número máximo de análisis a recuperar
            
        Returns:
            Lista de análisis ordenados cronológicamente (más recientes primero)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT symbol, timeframe, prompt, response, timestamp 
            FROM analyses 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        analyses = cursor.fetchall()
        conn.close()
        
        # Convertir a formato de lista de diccionarios
        result = [
            {
                "symbol": a[0], 
                "timeframe": a[1], 
                "prompt": a[2], 
                "response": a[3],
                "timestamp": a[4]
            }
            for a in analyses
        ]
        
        return result
    
    def get_most_recent_analysis(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene el análisis más reciente de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            
        Returns:
            Diccionario con el análisis más reciente o None si no hay análisis
        """
        recent = self.get_recent_analyses(user_id, limit=1)
        return recent[0] if recent else None
    
    def format_conversation_for_prompt(self, user_id: int, limit: int = 5) -> List[Dict[str, str]]:
        """
        Formatea el historial de conversación para incluirlo en el prompt de OpenAI.
        
        Args:
            user_id: ID del usuario de Telegram
            limit: Número máximo de mensajes a incluir
            
        Returns:
            Lista de mensajes en formato compatible con OpenAI
        """
        history = self.get_conversation_history(user_id, limit=limit)
        
        # Convertir al formato esperado por OpenAI
        formatted = []
        for msg in history:
            # Mapear 'assistant' a 'assistant' y cualquier otro valor a 'user'
            role = msg["role"] if msg["role"] == "assistant" else "user"
            formatted.append({
                "role": role,
                "content": msg["content"]
            })
        
        return formatted
    
    def get_user_context_summary(self, user_id: int) -> str:
        """
        Genera un resumen del contexto del usuario para incluir en el prompt.
        
        Args:
            user_id: ID del usuario de Telegram
            
        Returns:
            String con información contextual sobre el usuario
        """
        user = self.get_user(user_id)
        if not user:
            return ""
        
        recent_analysis = self.get_most_recent_analysis(user_id)
        
        context_parts = []
        
        # Añadir información sobre símbolos preferidos
        if user["preferred_symbols"]:
            symbols_str = ", ".join(user["preferred_symbols"])
            context_parts.append(f"Criptomonedas frecuentemente consultadas: {symbols_str}")
        
        # Añadir información sobre timeframes preferidos
        if user["preferred_timeframes"]:
            timeframes_str = ", ".join(user["preferred_timeframes"])
            context_parts.append(f"Timeframes frecuentemente utilizados: {timeframes_str}")
        
        # Añadir información sobre el análisis más reciente
        if recent_analysis:
            context_parts.append(
                f"Último análisis: {recent_analysis['symbol']} en timeframe {recent_analysis['timeframe']}"
            )
        
        return "\n".join(context_parts)
        
    # Métodos para gestión de alertas
    
    def create_alert(self, user_id: int, symbol: str, condition_type: str, 
                    condition_value: float, timeframe: str = "1h") -> int:
        """
        Crea una nueva alerta para un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            symbol: Símbolo de la criptomoneda (ej: BTC)
            condition_type: Tipo de condición ('price_above', 'price_below', 'rsi_above', etc.)
            condition_value: Valor umbral para la condición
            timeframe: Marco temporal para la alerta
            
        Returns:
            ID de la alerta creada
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Asegurarse de que el usuario existe
        user = self.get_user(user_id)
        if not user:
            self.create_or_update_user(user_id)
        
        # Crear alerta
        cursor.execute(
            """
            INSERT INTO alerts 
            (user_id, symbol, condition_type, condition_value, timeframe, is_active, last_checked)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (user_id, symbol, condition_type, condition_value, timeframe, datetime.now().isoformat())
        )
        
        alert_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return alert_id
    
    def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene las alertas de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            active_only: Si es True, solo devuelve alertas activas
            
        Returns:
            Lista de alertas
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute(
                """
                SELECT id, symbol, condition_type, condition_value, timeframe, 
                       is_active, created_at, last_checked, notification_sent
                FROM alerts
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
        else:
            cursor.execute(
                """
                SELECT id, symbol, condition_type, condition_value, timeframe, 
                       is_active, created_at, last_checked, notification_sent
                FROM alerts
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
        
        alerts_data = cursor.fetchall()
        conn.close()
        
        # Convertir a lista de diccionarios
        alerts = []
        for alert in alerts_data:
            alerts.append({
                "id": alert[0],
                "symbol": alert[1],
                "condition_type": alert[2],
                "condition_value": alert[3],
                "timeframe": alert[4],
                "is_active": bool(alert[5]),
                "created_at": alert[6],
                "last_checked": alert[7],
                "notification_sent": bool(alert[8])
            })
        
        return alerts
    
    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una alerta específica por su ID.
        
        Args:
            alert_id: ID de la alerta
            
        Returns:
            Diccionario con la información de la alerta o None si no existe
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, user_id, symbol, condition_type, condition_value, timeframe, 
                   is_active, created_at, last_checked, notification_sent
            FROM alerts
            WHERE id = ?
            """,
            (alert_id,)
        )
        
        alert_data = cursor.fetchone()
        conn.close()
        
        if not alert_data:
            return None
        
        # Convertir a diccionario
        alert = {
            "id": alert_data[0],
            "user_id": alert_data[1],
            "symbol": alert_data[2],
            "condition_type": alert_data[3],
            "condition_value": alert_data[4],
            "timeframe": alert_data[5],
            "is_active": bool(alert_data[6]),
            "created_at": alert_data[7],
            "last_checked": alert_data[8],
            "notification_sent": bool(alert_data[9])
        }
        
        return alert
    
    def update_alert(self, alert_id: int, is_active: Optional[bool] = None, 
                    notification_sent: Optional[bool] = None) -> bool:
        """
        Actualiza el estado de una alerta.
        
        Args:
            alert_id: ID de la alerta
            is_active: Nuevo estado de activación
            notification_sent: Nuevo estado de notificación
            
        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verificar que la alerta existe
        alert = self.get_alert(alert_id)
        if not alert:
            conn.close()
            return False
        
        # Construir la consulta de actualización
        update_parts = []
        params = []
        
        if is_active is not None:
            update_parts.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        if notification_sent is not None:
            update_parts.append("notification_sent = ?")
            params.append(1 if notification_sent else 0)
        
        # Siempre actualizar last_checked
        update_parts.append("last_checked = ?")
        params.append(datetime.now().isoformat())
        
        # Si no hay nada que actualizar
        if not update_parts:
            conn.close()
            return True
        
        # Ejecutar la actualización
        query = f"UPDATE alerts SET {', '.join(update_parts)} WHERE id = ?"
        params.append(alert_id)
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return True
    
    def get_user_custom_cryptos(self, user_id: int) -> List[str]:
        """
        Obtiene la lista personalizada de criptomonedas del usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            
        Returns:
            Lista de símbolos de criptomonedas personalizados
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT custom_cryptos FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return json.loads(result[0])
            return []
        except Exception as e:
            print(f"Error al obtener lista de criptomonedas: {e}")
            return []

    def save_user_custom_cryptos(self, user_id: int, cryptos: List[str]) -> bool:
        """
        Guarda la lista personalizada de criptomonedas del usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            cryptos: Lista de símbolos de criptomonedas
            
        Returns:
            True si la operación fue exitosa, False en caso contrario
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET custom_cryptos = ? WHERE user_id = ?",
                (json.dumps(cryptos), user_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al guardar lista de criptomonedas: {e}")
            return False
    
    def delete_alert(self, alert_id: int) -> bool:
        """
        Elimina una alerta.
        
        Args:
            alert_id: ID de la alerta
            
        Returns:
            True si la eliminación fue exitosa, False en caso contrario
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verificar que la alerta existe
        alert = self.get_alert(alert_id)
        if not alert:
            conn.close()
            return False
        
        # Eliminar la alerta
        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        conn.close()
        
        return True
    
    def get_all_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las alertas activas de todos los usuarios.
        Útil para el servicio de verificación de alertas.
        
        Returns:
            Lista de alertas activas
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, user_id, symbol, condition_type, condition_value, timeframe, 
                   created_at, last_checked, notification_sent
            FROM alerts
            WHERE is_active = 1
            """
        )
        
        alerts_data = cursor.fetchall()
        conn.close()
        
        # Convertir a lista de diccionarios
        alerts = []
        for alert in alerts_data:
            alerts.append({
                "id": alert[0],
                "user_id": alert[1],
                "symbol": alert[2],
                "condition_type": alert[3],
                "condition_value": alert[4],
                "timeframe": alert[5],
                "created_at": alert[6],
                "last_checked": alert[7],
                "notification_sent": bool(alert[8])
            })
        
        return alerts
