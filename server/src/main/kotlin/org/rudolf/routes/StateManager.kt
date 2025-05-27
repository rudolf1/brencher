package org.rudolf.routes

import kotlinx.coroutines.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import dto.*
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
        if (updatedRelease != null) saveState()
        return updatedRelease
    }

    suspend fun deleteRelease(name: String): Boolean {
        var removed = false
        state.updateAndGet { current ->
            val newList = current.releases.filterNot { it.name == name }
            removed = newList.size != current.releases.size
            current.copy(releases = newList)
        }
        if (removed) saveState()
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
