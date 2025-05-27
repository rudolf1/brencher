package org.rudolf

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import dto.ReleaseDto
import kotlinx.serialization.json.Json
import org.w3c.dom.WebSocket

@Composable
fun useReleaseWebSocket(onReleaseUpdate: (ReleaseDto) -> Unit, onError: (String) -> Unit) {
    val wsUrl = remember { "ws://localhost:8080/ws/releases" }
    DisposableEffect(Unit) {
        val ws = WebSocket(wsUrl)
        ws.onmessage = { event ->
            try {
                val release = Json.decodeFromString<ReleaseDto>(event.data as String)
                onReleaseUpdate(release)
            } catch (e: Exception) {
                onError("WebSocket parse error: ${e.message}")
            }
        }
        ws.onerror = { event ->
            onError("WebSocket error: $event")
        }
        onDispose { ws.close() }
    }
}
