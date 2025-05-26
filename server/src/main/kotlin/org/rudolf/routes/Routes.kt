package org.rudolf.routes

import io.ktor.http.*
import io.ktor.server.request.*
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.*
import dto.*
import org.rudolf.GitService

val releases = mutableListOf<ReleaseDto>()
val environments = mutableListOf<EnvironmentDto>()

fun Route.gitRoutes() {
    post("/branches") {
        val repoUrl = call.receive<String>()
        val branches = GitService.fetchBranches(repoUrl)
        call.respond(branches)
    }
}

fun Route.releaseRoutes() {
    route("/releases") {
        get {
            call.respond(releases)
        }
        
        post {
            val release = call.receive<ReleaseDto>()
            releases.add(release)
            call.respond(release)
        }
        
        put("/{name}/branches") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val branches = call.receive<List<String>>()
            val release = releases.find { it.name == name } ?: return@put call.respondText("Release not found", status = HttpStatusCode.NotFound)
            releases.remove(release)
            releases.add(release.copy(branches = branches))
            call.respond(releases)
        }
        
        put("/{name}/state") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val state = call.receive<ReleaseState>()
            val release = releases.find { it.name == name } ?: return@put call.respondText("Release not found", status = HttpStatusCode.NotFound)
            releases.remove(release)
            releases.add(release.copy(state = state))
            call.respond(releases)
        }
        
        put("/{name}/environment") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val environment = call.receive<String>()
            val release = releases.find { it.name == name } ?: return@put call.respondText("Release not found", status = HttpStatusCode.NotFound)
            releases.remove(release)
            releases.add(release.copy(environment = environment))
            call.respond(releases)
        }
        
        delete("/{name}") {
            val name = call.parameters["name"] ?: return@delete call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            releases.removeIf { it.name == name }
            call.respondText("Release removed")
        }
    }
}

fun Route.environmentRoutes() {
    route("/environments") {
        get {
            call.respond(environments)
        }
        
        post {
            val environment = call.receive<EnvironmentDto>()
            environments.add(environment)
            call.respond(environment)
        }
        
        put("/{name}") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val updatedEnvironment = call.receive<EnvironmentDto>()
            val index = environments.indexOfFirst { it.name == name }
            if (index == -1) return@put call.respondText("Environment not found", status = HttpStatusCode.NotFound)
            environments[index] = updatedEnvironment
            call.respond(updatedEnvironment)
        }
        
        delete("/{name}") {
            val name = call.parameters["name"] ?: return@delete call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            environments.removeIf { it.name == name }
            call.respondText("Environment removed")
        }
    }
}