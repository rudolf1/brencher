package org.rudolf.routes

import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import dto.*
import java.io.File
import kotlin.time.Duration.Companion.minutes

@Serializable
private data class StateData(
    val releases: List<ReleaseDto> = emptyList(),
    val environments: List<EnvironmentDto> = emptyList()
)

object StateManager {
    private val mutex = Mutex()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val releases = mutableListOf<ReleaseDto>()
    private val environments = mutableListOf<EnvironmentDto>()
    private val stateFile = File("state.json")
    private val json = Json { prettyPrint = true }

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
                val state = json.decodeFromString<StateData>(stateFile.readText())
                releases.clear()
                releases.addAll(state.releases)
                environments.clear()
                environments.addAll(state.environments)
            } catch (e: Exception) {
                println("Failed to load state: ${e.message}")
            }
        }
    }

    private suspend fun saveState() = mutex.withLock {
        try {
            val state = StateData(
                releases = releases.toList(),
                environments = environments.toList()
            )
            stateFile.writeText(json.encodeToString(StateData.serializer(), state))
        } catch (e: Exception) {
            println("Failed to save state: ${e.message}")
        }
    }

    suspend fun getReleases(): List<ReleaseDto> = mutex.withLock { releases.toList() }
    
    suspend fun addRelease(release: ReleaseDto) = mutex.withLock {
        releases.add(release)
        saveState()
    }

    suspend fun updateRelease(name: String, update: (ReleaseDto) -> ReleaseDto): ReleaseDto? = mutex.withLock {
        val index = releases.indexOfFirst { it.name == name }
        if (index != -1) {
            val updated = update(releases[index])
            releases[index] = updated
            saveState()
            updated
        } else null
    }

    suspend fun deleteRelease(name: String): Boolean = mutex.withLock {
        val result = releases.removeIf { it.name == name }
        if (result) saveState()
        result
    }

    suspend fun getEnvironments(): List<EnvironmentDto> = mutex.withLock { environments.toList() }
    
    suspend fun addEnvironment(environment: EnvironmentDto) = mutex.withLock {
        environments.add(environment)
        saveState()
    }

    suspend fun updateEnvironment(environment: EnvironmentDto): Boolean = mutex.withLock {
        val index = environments.indexOfFirst { it.name == environment.name }
        if (index != -1) {
            environments[index] = environment
            saveState()
            true
        } else false
    }

    suspend fun deleteEnvironment(name: String): Boolean = mutex.withLock {
        val result = environments.removeIf { it.name == name }
        if (result) saveState()
        result
    }
}
