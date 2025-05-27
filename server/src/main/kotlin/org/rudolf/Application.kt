package org.rudolf

import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.http.content.staticResources
import io.ktor.server.netty.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.plugins.cors.routing.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.coroutines.*
import kotlinx.serialization.json.Json
import org.rudolf.routes.gitRoutes
import org.rudolf.routes.releaseRoutes
import org.rudolf.routes.environmentRoutes

fun main(args: Array<String>): Unit = io.ktor.server.netty.EngineMain.main(args)

fun Application.module() {
    val config = environment.config
    var repositoryUrl = config.property("ktor.git.repositoryUrl").getString()
    var branchRefreshIntervalMinutes = config.property("ktor.git.branchRefreshIntervalMinutes").getString().toInt()
    GitService.configure(repositoryUrl, branchRefreshIntervalMinutes)

    // Periodically reload config and reconfigure GitService if changed
    launch {
        while (true) {
            delay(60_000) // Check every 60 seconds
            val newRepositoryUrl = config.property("ktor.git.repositoryUrl").getString()
            val newBranchRefreshIntervalMinutes = config.property("ktor.git.branchRefreshIntervalMinutes").getString().toInt()
            if (newRepositoryUrl != repositoryUrl || newBranchRefreshIntervalMinutes != branchRefreshIntervalMinutes) {
                repositoryUrl = newRepositoryUrl
                branchRefreshIntervalMinutes = newBranchRefreshIntervalMinutes
                GitService.configure(repositoryUrl, branchRefreshIntervalMinutes)
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
    
    routing {
        gitRoutes()
        releaseRoutes()
        environmentRoutes()
        staticResources("/", "www")
    }

}
