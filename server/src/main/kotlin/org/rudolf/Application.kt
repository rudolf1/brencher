package org.rudolf

import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.http.content.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.plugins.cors.routing.*
import io.ktor.server.routing.*
import io.ktor.server.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import org.rudolf.routes.environmentRoutes
import org.rudolf.routes.gitRoutes
import org.rudolf.routes.releaseRoutes
import kotlin.time.Duration.Companion.seconds

fun main(args: Array<String>): Unit = io.ktor.server.netty.EngineMain.main(args)

fun Application.module() {
    val config = environment.config
    var repositoryUrl = config.property("ktor.git.repositoryUrl").getString()
    var branchRefreshIntervalMinutes = config.property("ktor.git.branchRefreshIntervalMinutes").getString().toInt()
    val gitUsername = config.propertyOrNull("ktor.git.username")?.getString() ?: ""
    val gitPassword = config.propertyOrNull("ktor.git.password")?.getString() ?: ""
    GitService.configure(repositoryUrl, branchRefreshIntervalMinutes, gitUsername, gitPassword)

    // Periodically reload config and reconfigure GitService if changed
    launch {
        while (true) {
            delay(60_000) // Check every 60 seconds
            val newRepositoryUrl = config.property("ktor.git.repositoryUrl").getString()
            val newBranchRefreshIntervalMinutes = config.property("ktor.git.branchRefreshIntervalMinutes").getString().toInt()
            val newGitUsername = config.propertyOrNull("ktor.git.username")?.getString() ?: ""
            val newGitPassword = config.propertyOrNull("ktor.git.password")?.getString() ?: ""
            if (newRepositoryUrl != repositoryUrl || newBranchRefreshIntervalMinutes != branchRefreshIntervalMinutes || newGitUsername != gitUsername || newGitPassword != gitPassword) {
                repositoryUrl = newRepositoryUrl
                branchRefreshIntervalMinutes = newBranchRefreshIntervalMinutes
                GitService.configure(repositoryUrl, branchRefreshIntervalMinutes, newGitUsername, newGitPassword)
            }
        }
    }

    // Background job: subscribe to Release updates and process merges
    launch {
        val channel = org.rudolf.routes.StateManager.releaseUpdatesChannel
        for (release in channel) {
            // Check if auto/<hash> is up-to-date, else merge and push
            val result = org.rudolf.GitService.mergeBranchesAndPushAutoBranch(release.branches)
            // Optionally: log or notify if needed (UI is notified via API responses)
            if (result.isFailure) {
                println("[Release Merge] Failed for ${release.name}: ${result.exceptionOrNull()?.message}")
            } else {
                println("[Release Merge] Success for ${release.name}: ${result.getOrNull()}")
            }
        }
    }

    install(ContentNegotiation) {
        json(Json {
            prettyPrint = true
            isLenient = true
        })
    }

    install(CORS) {
        anyHost()
        allowHeader("Content-Type")
        allowMethod(io.ktor.http.HttpMethod.Get)
        allowMethod(io.ktor.http.HttpMethod.Post)
        allowMethod(io.ktor.http.HttpMethod.Put)
        allowMethod(io.ktor.http.HttpMethod.Delete)
    }

    install(WebSockets) {
        pingPeriod = 15.seconds
        timeout = 30.seconds
        maxFrameSize = Long.MAX_VALUE
        masking = false
    }

    routing {
        gitRoutes()
        releaseRoutes()
        environmentRoutes()
        staticResources("/", "www")
        webSocket("/ws/releases") {
            // Stream release updates to connected clients
            val flow = org.rudolf.routes.StateManager.releaseUpdatesFlow
            val job = launch {
                flow.collect { release ->
                    val json = Json.encodeToString(release)
                    send(Frame.Text(json))
                }
            }
            try {
                // Keep the connection open
                for (frame in incoming) {
                    // Optionally handle incoming messages
                }
            } finally {
                job.cancel()
            }
        }
    }

}
