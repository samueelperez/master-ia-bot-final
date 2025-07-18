# Crypto AI Bot - Interfaz Web

Esta es la interfaz web para el proyecto Crypto AI Bot, una plataforma de análisis de criptomonedas basada en inteligencia artificial.

## Características

- **Análisis de Criptomonedas**: Obtén análisis técnicos y predictivos para diferentes criptomonedas.
- **Estrategias de Trading**: Explora estrategias de trading optimizadas por IA para diferentes perfiles de riesgo.
- **Interfaz Moderna**: Diseño moderno y responsive con Tailwind CSS.
- **Integración con IA**: Conecta con modelos de IA para análisis avanzados.

## Tecnologías Utilizadas

- **Next.js**: Framework de React para renderizado del lado del servidor y generación de sitios estáticos.
- **React**: Biblioteca JavaScript para construir interfaces de usuario.
- **Tailwind CSS**: Framework de CSS utilitario para diseño rápido y responsivo.
- **Supabase**: Base de datos y autenticación.

## Estructura del Proyecto

```
webapp/
├── public/             # Archivos estáticos
├── src/                # Código fuente
│   ├── app/            # Rutas de la aplicación (Next.js App Router)
│   │   ├── analysis/   # Página de análisis de criptomonedas
│   │   ├── strategies/ # Página de estrategias de trading
│   │   ├── globals.css # Estilos globales
│   │   ├── layout.tsx  # Layout principal
│   │   └── page.js     # Página principal
│   ├── lib/            # Utilidades y servicios
│   │   ├── api.ts      # Funciones para llamadas a API
│   │   └── supabase.ts # Cliente de Supabase
│   └── types/          # Definiciones de tipos TypeScript
└── ...
```

## Integración con el Backend

La interfaz web se comunica con el backend a través de una API REST. El backend proporciona:

- Análisis técnico de criptomonedas
- Predicciones de precios basadas en IA
- Estrategias de trading optimizadas
- Datos históricos para visualizaciones

## Integración con el Módulo de IA

La aplicación se integra con el módulo de IA (ai-module) que proporciona:

- Análisis de sentimiento de mercado
- Predicciones de precios
- Optimización de parámetros para estrategias de trading
- Recomendaciones personalizadas

## Desarrollo Local

1. Clona el repositorio
2. Instala las dependencias:
   ```bash
   cd webapp
   npm install
   ```
3. Configura las variables de entorno:
   ```
   # Crea un archivo .env.local con las siguientes variables
   NEXT_PUBLIC_SUPABASE_URL=tu_url_de_supabase
   NEXT_PUBLIC_SUPABASE_ANON_KEY=tu_clave_anonima_de_supabase
   NEXT_PUBLIC_API_URL=url_de_tu_api
   ```
4. Inicia el servidor de desarrollo:
   ```bash
   npm run dev
   ```
5. Abre [http://localhost:3000](http://localhost:3000) en tu navegador.

## Despliegue

La aplicación puede ser desplegada en cualquier plataforma que soporte Next.js, como Vercel, Netlify o un servidor propio.

```bash
# Construir la aplicación para producción
npm run build

# Iniciar en modo producción
npm start
```

## Próximas Mejoras

- Implementación de autenticación de usuarios
- Panel de control personalizado
- Notificaciones en tiempo real
- Integración con exchanges para trading automatizado
- Visualizaciones avanzadas de datos
