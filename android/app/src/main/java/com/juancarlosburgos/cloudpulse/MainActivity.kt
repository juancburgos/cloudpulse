package com.juancarlosburgos.cloudpulse

import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * CloudPulse — app de portafolio.
 * Consulta el estado de su propia API en producción (FastAPI + PostgreSQL).
 * Componentes: red HTTPS, parseo JSON, estados de error/offline, reintento y refresco automático.
 */
class MainActivity : AppCompatActivity() {

    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(8, TimeUnit.SECONDS)
        .build()

    private val scope = CoroutineScope(Dispatchers.Main)
    private var refreshJob: Job? = null
    private var loading = false

    private lateinit var tvApiState: TextView
    private lateinit var tvVersion: TextView
    private lateinit var tvRegion: TextView
    private lateinit var tvUptime: TextView
    private lateinit var tvDbState: TextView
    private lateinit var tvDbLatency: TextView
    private lateinit var tvPings: TextView
    private lateinit var tvLastPing: TextView
    private lateinit var btnPing: Button
    private lateinit var tvError: TextView

    private val baseUrl = BuildConfig.API_BASE_URL

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvApiState = findViewById(R.id.tvApiState)
        tvVersion = findViewById(R.id.tvVersion)
        tvRegion = findViewById(R.id.tvRegion)
        tvUptime = findViewById(R.id.tvUptime)
        tvDbState = findViewById(R.id.tvDbState)
        tvDbLatency = findViewById(R.id.tvDbLatency)
        tvPings = findViewById(R.id.tvPings)
        tvLastPing = findViewById(R.id.tvLastPing)
        tvError = findViewById(R.id.tvError)
        btnPing = findViewById(R.id.btnPing)
        findViewById<TextView>(R.id.tvApiUrl).text = baseUrl

        btnPing.setOnClickListener { sendPing() }
        findViewById<Button>(R.id.btnRefresh).setOnClickListener { refresh() }

        refresh()
    }

    override fun onResume() {
        super.onResume()
        refreshJob = scope.launch {
            while (true) {
                delay(15_000)
                refresh(silent = true)
            }
        }
    }

    override fun onPause() {
        super.onPause()
        refreshJob?.cancel()
    }

    private fun refresh(silent: Boolean = false) {
        if (loading) return
        scope.launch {
            loading = true
            if (!silent) setError("Consultando API…", Color.parseColor("#8FA3BF"))
            try {
                val json = withContext(Dispatchers.IO) { get("$baseUrl/api/v1/status") }
                renderStatus(json)
                setError("", Color.TRANSPARENT)
            } catch (e: Exception) {
                renderOffline()
                setError("No se pudo contactar la API. Revisa tu conexión y reintenta.", Color.parseColor("#F87171"))
            } finally {
                loading = false
            }
        }
    }

    private fun sendPing() {
        if (loading) return
        scope.launch {
            loading = true
            btnPing.isEnabled = false
            btnPing.text = "Enviando…"
            try {
                val json = withContext(Dispatchers.IO) { post("$baseUrl/api/v1/ping") }
                setError("Ping registrado ✔ (fila ${json.optLong("db_row_id")} en PostgreSQL)", Color.parseColor("#34D399"))
                renderStatus(json)
            } catch (e: Exception) {
                setError("Ping falló: sin conexión con la API.", Color.parseColor("#F87171"))
            } finally {
                loading = false
                btnPing.isEnabled = true
                btnPing.text = "Enviar ping"
            }
        }
    }

    private fun renderStatus(json: JSONObject) {
        val db = json.optJSONObject("database")
        val server = json.optJSONObject("server")
        val status = json.optString("status", "unknown")

        tvApiState.text = if (status == "ok") "● Operativo" else "● Degradado"
        tvApiState.setTextColor(if (status == "ok") Color.parseColor("#34D399") else Color.parseColor("#FBBF24"))

        tvVersion.text = json.optString("version", "—")
        tvRegion.text = server?.optString("region", "—") ?: "—"
        tvUptime.text = humanUptime(json.optLong("server_uptime_s", -1).let {
            server?.optLong("uptime_s", -1) ?: it
        })
        tvDbState.text = if (db?.optString("status") == "up") "Conectada" else "Caída"
        tvDbState.setTextColor(if (db?.optString("status") == "up") Color.parseColor("#34D399") else Color.parseColor("#F87171"))
        tvDbLatency.text = if (db?.has("latency_ms") == true) "${db.optLong("latency_ms")} ms" else "—"
        tvPings.text = if (db?.has("total_pings") == true) db.optLong("total_pings").toString() else "—"
        tvLastPing.text = db?.optString("last_ping_at")?.take(19)?.replace("T", " ") ?: "—"
    }

    private fun renderOffline() {
        tvApiState.text = "● Sin conexión"
        tvApiState.setTextColor(Color.parseColor("#F87171"))
    }

    private fun setError(msg: String, color: Int) {
        tvError.text = msg
        tvError.setTextColor(color)
    }

    private fun humanUptime(seconds: Long): String {
        if (seconds < 0) return "—"
        val d = seconds / 86400; val h = (seconds % 86400) / 3600
        val m = (seconds % 3600) / 60
        return if (d > 0) "${d}d ${h}h" else if (h > 0) "${h}h ${m}m" else "${m}m"
    }

    private fun get(url: String): JSONObject {
        val req = Request.Builder().url(url).get().build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string() ?: throw RuntimeException("sin respuesta")
            if (!resp.isSuccessful) throw RuntimeException("HTTP ${resp.code}")
            return JSONObject(body)
        }
    }

    private fun post(url: String): JSONObject {
        val req = Request.Builder().url(url).post(okhttp3.RequestBody.create(null, ByteArray(0))).build()
        client.newCall(req).execute().use { resp ->
            val body = resp.body?.string() ?: throw RuntimeException("sin respuesta")
            if (!resp.isSuccessful) throw RuntimeException("HTTP ${resp.code}")
            return JSONObject(body)
        }
    }
}
