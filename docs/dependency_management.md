# Gestión de Dependencias Consolidada

## 📋 Resumen

Las dependencias del proyecto han sido consolidadas para resolver conflictos de versiones y simplificar el mantenimiento.

## 🗂️ Estructura

```
requirements/
├── common.txt           # Dependencias compartidas entre módulos
├── ai-module.txt       # Específicas del módulo de IA
├── backend.txt         # Específicas del backend
├── external-data.txt   # Específicas del servicio de datos externos
├── testing.txt         # Dependencias de desarrollo y testing
└── constraints.txt     # Control estricto de versiones
```

## 🚀 Instalación

### Para Desarrollo Local

```bash
# Instalar dependencias de un módulo específico
pip install -c requirements/constraints.txt -r requirements/ai-module.txt

# Instalar dependencias de desarrollo
pip install -c requirements/constraints.txt -r requirements/testing.txt
```

### Para Producción

```bash
# Los Dockerfiles ya están configurados para usar la nueva estructura
docker-compose up --build
```

## 🔧 Resolución de Conflictos

### Conflictos Resueltos:

1. **Pydantic v1 vs v2**: Migrado todo a v2.5.2
2. **FastAPI inconsistente**: Unificado en v0.104.1
3. **Dependencias sin versión**: Todas fijadas a versiones estables

### Versiones Unificadas:

- `fastapi==0.104.1`
- `pydantic==2.5.2` (MIGRACIÓN de v1 a v2)
- `uvicorn==0.24.0`
- `httpx==0.25.2`
- `aiogram==3.2.0` (antes sin versión)
- `ccxt==4.1.65` (antes sin versión)
- `redis==5.0.1` (antes sin versión)

## ⚠️ Migración Pydantic v1 → v2

### Cambios Principales:

```python
# Antes (Pydantic v1)
from pydantic import BaseModel

class User(BaseModel):
    name: str
    
    class Config:
        arbitrary_types_allowed = True

# Ahora (Pydantic v2)
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
```

### Archivos que Requieren Actualización:

- `external-data-service/models/schemas.py`
- Cualquier archivo que use `class Config:`

## 🔄 Flujo de Actualización

### Para Añadir Nueva Dependencia:

1. **Añadir a archivo específico** (`requirements/ai-module.txt`)
2. **Actualizar constraints.txt** con versión fija
3. **Probar instalación** en entorno limpio
4. **Actualizar documentación**

### Para Actualizar Versión:

1. **Modificar constraints.txt**
2. **Probar en todos los módulos**
3. **Actualizar si hay breaking changes**

## 🧪 Testing

```bash
# Instalar dependencias de testing
pip install -c requirements/constraints.txt -r requirements/testing.txt

# Ejecutar tests
pytest

# Verificar seguridad
safety check -r requirements/constraints.txt
```

## 📞 Troubleshooting

### Error: "No matching distribution"
- Verificar que la versión existe en PyPI
- Comprobar compatibilidad con Python 3.10

### Error: "Conflicting dependencies"
- Verificar que constraints.txt esté actualizado
- Usar `pip freeze` para debug

### Error de importación después de migración
- Revisar cambios Pydantic v1 → v2
- Actualizar sintaxis de configuración

---

*Dependencias consolidadas automáticamente el 2025-06-19 18:40:21*
