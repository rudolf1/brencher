package org.rudolf.routes

import dto.*
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.util.concurrent.atomic.AtomicReference
import kotlin.time.Duration.Companion.minutes

@Serializable
private data class StateData(
    val releases: List<ReleaseDto> = emptyList(),
    val environments: List<EnvironmentDto> = emptyList()
)

object StateManager {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val stateFile = File("/media/DATA/src/brencher/testState/state.json")
    private val json = Json { prettyPrint = true }
    private val state = AtomicReference(StateData())

    // Channel to broadcast Release state updates
    val releaseUpdatesChannel = Channel<ReleaseDto>(Channel.BUFFERED)
    // Optionally, a SharedFlow for coroutine-friendly subscriptions
    private val _releaseUpdatesFlow = MutableSharedFlow<ReleaseDto>(replay = 0, extraBufferCapacity = 64)
    val releaseUpdatesFlow = _releaseUpdatesFlow.asSharedFlow()

    init {
        loadState()
        scope.launch {
            while (isActive) {
                delay(5.minutes)
                saveState()
            }
        }
    }

    private fun loadState() {
        if (stateFile.exists()) {
            try {
                val loaded = json.decodeFromString<StateData>(stateFile.readText())
                state.set(loaded)
            } catch (e: Exception) {
                println("Failed to load state: ${e.message}")
            }
        }
    }

    private fun saveState() {
        try {
            stateFile.writeText(json.encodeToString(StateData.serializer(), state.get()))
        } catch (e: Exception) {
            println("Failed to save state: ${e.message}")
        }
    }

    suspend fun getReleases(): List<ReleaseDto> = state.get().releases

    suspend fun addRelease(release: ReleaseDto) {
        state.updateAndGet { it.copy(releases = it.releases + release) }
        saveState()
        releaseUpdatesChannel.send(release)
        _releaseUpdatesFlow.emit(release)
    }

    suspend fun updateRelease(name: String, update: (ReleaseDto) -> ReleaseDto): ReleaseDto? {
        var updatedRelease: ReleaseDto? = null
        state.updateAndGet { current ->
            val idx = current.releases.indexOfFirst { it.name == name }
            if (idx != -1) {
                updatedRelease = update(current.releases[idx])
                current.copy(releases = current.releases.toMutableList().apply { set(idx, updatedRelease!!) })
            } else {
                current
            }
        }
        if (updatedRelease != null) {
            saveState()
            releaseUpdatesChannel.send(updatedRelease!!)
            _releaseUpdatesFlow.emit(updatedRelease!!)
        }
        return updatedRelease
    }

    suspend fun deleteRelease(name: String): Boolean {
        var removed = false
        var deleted: ReleaseDto? = null
        state.updateAndGet { current ->
            val newList = current.releases.filterNot { it.name == name }
            removed = newList.size != current.releases.size
            if (removed) {
                deleted = current.releases.find { it.name == name }
            }
            current.copy(releases = newList)
        }
        if (removed) {
            saveState()
            deleted?.let {
                releaseUpdatesChannel.send(it)
                _releaseUpdatesFlow.emit(it)
            }
        }
        return removed
    }

    suspend fun getEnvironments(): List<EnvironmentDto> = state.get().environments

    suspend fun addEnvironment(environment: EnvironmentDto) {
        state.updateAndGet { it.copy(environments = it.environments + environment) }
        saveState()
    }

    suspend fun updateEnvironment(environment: EnvironmentDto): Boolean {
        var updated = false
        state.updateAndGet { current ->
            val idx = current.environments.indexOfFirst { it.name == environment.name }
            if (idx != -1) {
                updated = true
                current.copy(environments = current.environments.toMutableList().apply { set(idx, environment) })
            } else {
                current
            }
        }
        if (updated) saveState()
        return updated
    }

    suspend fun deleteEnvironment(name: String): Boolean {
        var removed = false
        state.updateAndGet { current ->
            val newList = current.environments.filterNot { it.name == name }
            removed = newList.size != current.environments.size
            current.copy(environments = newList)
        }
        if (removed) saveState()
        return removed
    }
}
