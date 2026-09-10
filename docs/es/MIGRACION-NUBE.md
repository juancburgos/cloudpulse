# Guía de migración del VPS — Hostinger → Hetzner / DigitalOcean (nube barata)

> CloudPulse (y todo el stack VeloWhat) está pensado para migrar de proveedor en minutos.
> Esta guía es la prueba de que la arquitectura es portable (uno de los puntos de la entrevista de portafolio).

## Estado actual (sept 2026)

- VPS Hostinger `2.25.125.53` (srv1948046, KVM 2, 2 vCPU / 7.8 GB RAM / 96 GB disco).
- Caduca el **2026-10-01** → hay que migrar o renovar antes de esa fecha.
- Contenido: Caddy (proxy/TLS), n8n, `cloudpulse` stack (api+db), sitios estáticos, agente dsh.

## Paso 1 — Elegir el proveedor nuevo

| Proveedor | Precio típico | Nota |
|---|---|---|
| Hetzner CX22 | ~€4/mes (2 vCPU/4GB) | el mejor precio; requiere verificación de identidad/pago |
| DigitalOcean droplet | ~$6/mes | simple, amplia documentación |
| Contabo / OVH | ~€4–7/mes | alternativas baratas |
| Oracle Cloud Free | $0 | siempre-free tier ARM, setup más complejo |

Recomendado para esta carga: **Hetzner CX22** o el **CPX11 (~€3.5)** — el stack entero usa <2 GB RAM.

## Paso 2 — Preparar el nuevo servidor (Ubuntu 24.04)

```bash
# 1) instalar docker + compose plugin
curl -fsSL https://get.docker.com | sh

# 2) copiar el stack desde el VPS actual
rsync -av root@2.25.125.53:/opt/cloudpulse /opt/
# (o desde la laptop: /home/uses/Descargas/cloudpulse/backend + deploy/)

# 3) levantar api + db
cd /opt/cloudpulse && docker compose up -d --build
```

## Paso 3 — Proxy reverso TLS (Caddy, igual que hoy)

En el nuevo VPS, o bien:
- **Opción A (recomendada):** copiar `/opt/caddy` del VPS actual (Caddyfile + compose con volúmenes) y
  montar además `/opt/cloudpulse`-web; o
- **Opción B:** instalar caddy standalone: `apt install caddy`, Caddyfile:

```
api.juancarlosburgosautor.com {
    reverse_proxy 127.0.0.1:8001
}
cloudpulse.juancarlosburgosautor.com {
    root * /srv/cloudpulse-web
    file_server
}
```

Caddy emitirá los certificados Let's Encrypt automáticamente cuando el DNS apunte al nuevo IP.

## Paso 4 — DNS (Hostinger hPanel)

En `hpanel.hostinger.com → juancarlosburgosautor.com → DNS`:
- Cambiar el A record de `api` al nuevo IP.
- Cambiar el A record de `cloudpulse` al nuevo IP.
Propagación: minutos (TTL 300 recomendado).

> OJO: la app Android apunta a `https://api.juancarlosburgosautor.com` (hostname, no IP)
> → la migración NO requiere actualizar la app publicada. Ese es el punto de la arquitectura.

## Paso 5 — Verificar

```bash
curl -s https://api.juancarlosburgosautor.com/healthz     # {"status":"ok","db":"up",...}
curl -s https://api.juancarlosburgosautor.com/api/v1/status
```
Abrir la app CloudPulse → debería mostrar el estado en vivo contra el nuevo servidor.

## Costos y checklist

- [ ] Nuevo VPS creado y pagado (≈ $4–6/mes)
- [ ] Docker + stack desplegado
- [ ] Caddy configurado
- [ ] DNS actualizado (api + cloudpulse)
- [ ] Verificado healthz/status público
- [ ] n8n / otros servicios migrados (opcional; mismo patrón)
- [ ] VPS Hostinger dado de baja (o no renovado el 2026-10-01)
