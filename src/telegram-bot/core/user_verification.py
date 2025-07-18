"""
Sistema de gestión de verificación de usuarios para el bot.
Maneja el estado de verificación de referidos.
"""

import os
import sqlite3
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VerificationStatus:
    """Estado de verificación de un usuario."""
    user_id: int
    is_verified: bool
    verification_method: Optional[str] = None
    exchange_used: Optional[str] = None
    uid_verified: Optional[str] = None
    verified_at: Optional[datetime] = None
    attempts: int = 0
    last_attempt: Optional[datetime] = None

class UserVerificationManager:
    """Gestor de verificación de usuarios."""
    
    def __init__(self, db_path: str = "user_verification.db"):
        self.db_path = db_path
        self.max_attempts = 3
        self.attempt_cooldown = timedelta(hours=1)
        self._init_db()
    
    def _init_db(self):
        """Inicializa la base de datos de verificación."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_verification (
                user_id INTEGER PRIMARY KEY,
                is_verified BOOLEAN DEFAULT FALSE,
                verification_method TEXT,
                exchange_used TEXT,
                uid_verified TEXT,
                verified_at TIMESTAMP,
                attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Tabla para logs de intentos de verificación
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                exchange TEXT,
                exchange_uid TEXT,
                success BOOLEAN,
                error_message TEXT,
                attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_verification (user_id)
            )
            ''')
            
            conn.commit()
        
        # Actualizar estructura si es necesaria
        self._update_db_structure()
    
    def _update_db_structure(self):
        """Actualiza la estructura de la base de datos si es necesario."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Verificar si attempted_at existe en verification_attempts
            cursor.execute("PRAGMA table_info(verification_attempts)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'attempted_at' not in columns:
                # Agregar columna attempted_at si no existe
                cursor.execute('''
                    ALTER TABLE verification_attempts 
                    ADD COLUMN attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ''')
                conn.commit()
                logger.info("Estructura de base de datos actualizada: agregada columna attempted_at")
    
    def get_verification_status(self, user_id: int) -> VerificationStatus:
        """Obtiene el estado de verificación de un usuario."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, is_verified, verification_method, exchange_used, 
                       uid_verified, verified_at, attempts, last_attempt
                FROM user_verification WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            
            if row:
                return VerificationStatus(
                    user_id=row[0],
                    is_verified=bool(row[1]),
                    verification_method=row[2],
                    exchange_used=row[3],
                    uid_verified=row[4],
                    verified_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    attempts=row[6] or 0,
                    last_attempt=datetime.fromisoformat(row[7]) if row[7] else None
                )
            else:
                # Usuario nuevo, crear registro
                return self._create_user_record(user_id)
    
    def _create_user_record(self, user_id: int) -> VerificationStatus:
        """Crea un nuevo registro de usuario."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_verification (user_id, is_verified, attempts)
                VALUES (?, FALSE, 0)
            """, (user_id,))
            
            conn.commit()
        
        return VerificationStatus(
            user_id=user_id,
            is_verified=False,
            attempts=0
        )
    
    def can_attempt_verification(self, user_id: int) -> tuple[bool, str]:
        """
        Verifica si un usuario puede intentar verificarse.
        
        Returns:
            tuple[bool, str]: (puede_intentar, mensaje_error)
        """
        status = self.get_verification_status(user_id)
        
        if status.is_verified:
            return False, "Ya estás verificado"
        
        if status.attempts >= self.max_attempts:
            if status.last_attempt:
                cooldown_end = status.last_attempt + self.attempt_cooldown
                if datetime.now() < cooldown_end:
                    remaining = cooldown_end - datetime.now()
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    return False, f"Máximo de intentos excedido. Intenta en {hours}h {minutes}m"
                else:
                    # Reset attempts after cooldown
                    self._reset_attempts(user_id)
        
        return True, ""
    
    def _reset_attempts(self, user_id: int):
        """Resetea los intentos de un usuario después del cooldown."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_verification 
                SET attempts = 0, updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
    
    def record_verification_attempt(self, user_id: int, uid: str, success: bool, 
                                  exchange: Optional[str] = None, error_msg: Optional[str] = None):
        """Registra un intento de verificación."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Registrar en log de intentos usando la estructura correcta de la BD
            cursor.execute("""
                INSERT INTO verification_attempts 
                (user_id, exchange, exchange_uid, success, error_message, attempt_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, exchange or "unknown", uid, success, error_msg, datetime.now().timestamp()))
            
            # Actualizar estado del usuario
            if success:
                cursor.execute("""
                    UPDATE user_verification 
                    SET is_verified = TRUE, verification_method = 'referral',
                        exchange_used = ?, uid_verified = ?, verified_at = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (exchange, uid, datetime.now().isoformat(), 
                     datetime.now().isoformat(), user_id))
            else:
                cursor.execute("""
                    UPDATE user_verification 
                    SET attempts = attempts + 1, last_attempt = ?, updated_at = ?
                    WHERE user_id = ?
                """, (datetime.now().isoformat(), datetime.now().isoformat(), user_id))
            
            conn.commit()
    
    def mark_verified(self, user_id: int, method: str = "manual", exchange: Optional[str] = None, 
                     uid: Optional[str] = None):
        """Marca un usuario como verificado manualmente."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_verification 
                SET is_verified = TRUE, verification_method = ?, exchange_used = ?,
                    uid_verified = ?, verified_at = ?, updated_at = ?
                WHERE user_id = ?
            """, (method, exchange, uid, datetime.now().isoformat(), 
                 datetime.now().isoformat(), user_id))
            
            conn.commit()
    
    def is_verification_required(self) -> bool:
        """Verifica si la verificación de referidos está habilitada."""
        return os.getenv("REQUIRE_REFERRAL_VERIFICATION", "false").lower() == "true"
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de verificación."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total de usuarios
            cursor.execute("SELECT COUNT(*) FROM user_verification")
            total_users = cursor.fetchone()[0]
            
            # Usuarios verificados
            cursor.execute("SELECT COUNT(*) FROM user_verification WHERE is_verified = TRUE")
            verified_users = cursor.fetchone()[0]
            
            # Usuarios pendientes
            cursor.execute("SELECT COUNT(*) FROM user_verification WHERE is_verified = FALSE")
            pending_users = cursor.fetchone()[0]
            
            # Intentos fallidos en las últimas 24h
            yesterday_timestamp = (datetime.now() - timedelta(hours=24)).timestamp()
            cursor.execute("""
                SELECT COUNT(*) FROM verification_attempts 
                WHERE attempt_date > ? AND success = FALSE
            """, (yesterday_timestamp,))
            failed_attempts_24h = cursor.fetchone()[0]
            
            # Exchanges más usados
            cursor.execute("""
                SELECT exchange_used, COUNT(*) as count 
                FROM user_verification 
                WHERE is_verified = TRUE AND exchange_used IS NOT NULL
                GROUP BY exchange_used 
                ORDER BY count DESC
            """)
            exchange_stats = dict(cursor.fetchall())
            
            return {
                "total_users": total_users,
                "verified_users": verified_users,
                "pending_users": pending_users,
                "verification_rate": verified_users / total_users * 100 if total_users > 0 else 0,
                "failed_attempts_24h": failed_attempts_24h,
                "exchange_stats": exchange_stats
            }
    
    def cleanup_old_attempts(self, days: int = 30):
        """Limpia intentos antiguos de verificación."""
        cutoff_timestamp = (datetime.now() - timedelta(days=days)).timestamp()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM verification_attempts 
                WHERE attempt_date < ? AND success = FALSE
            """, (cutoff_timestamp,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"Limpiados {deleted} intentos de verificación antiguos")
            return deleted

# Instancia global del gestor
user_verification = UserVerificationManager() 