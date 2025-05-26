package org.rudolf.routes

import io.ktor.http.*
import io.ktor.server.request.*
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.*
import dto.*
import org.rudolf.GitService
import org.rudolf.config.JsonValidator

fun Route.gitRoutes() {
    route("/branches") {
        get {
            val branches = GitService.fetchBranches()
            call.respond(branches)
        }
        
        post {
            val repoUrl = call.receive<String>()
            val branches = GitService.fetchBranches(repoUrl)
            call.respond(branches)
        }
    }
}

fun Route.releaseRoutes() {
    route("/releases") {
        get {
            val releases = StateManager.getReleases()
            call.respond(releases)
        }
        
        post {
            val release = call.receive<ReleaseDto>()
            StateManager.addRelease(release)
            call.respond(release)
        }
        
        put("/{name}/branches") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val branches = call.receive<List<String>>()
            val updated = StateManager.updateRelease(name) { it.copy(branches = branches) }
                ?: return@put call.respondText("Release not found", status = HttpStatusCode.NotFound)
            call.respond(updated)
        }
        
        put("/{name}/state") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val state = call.receive<ReleaseState>()
            val updated = StateManager.updateRelease(name) { it.copy(state = state) }
                ?: return@put call.respondText("Release not found", status = HttpStatusCode.NotFound)
            call.respond(updated)
        }
        
        put("/{name}/environment") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val environment = call.receive<String>()
            val updated = StateManager.updateRelease(name) { it.copy(environment = environment) }
                ?: return@put call.respondText("Release not found", status = HttpStatusCode.NotFound)
            call.respond(updated)
        }
        
        delete("/{name}") {
            val name = call.parameters["name"] ?: return@delete call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            if (StateManager.deleteRelease(name)) {
                call.respond(HttpStatusCode.OK)
            } else {
                call.respondText("Release not found", status = HttpStatusCode.NotFound)
            }
        }
    }
}

fun Route.environmentRoutes() {
    route("/environments") {
        get {
            val environments = StateManager.getEnvironments()
            call.respond(environments)
        }
        
        post {
            val environment = call.receive<EnvironmentDto>()
            if (!JsonValidator.isValidJson(environment.configuration)) {
                return@post call.respondText("Invalid JSON configuration", status = HttpStatusCode.BadRequest)
            }
            environment.copy(configuration = JsonValidator.formatJson(environment.configuration)).let {
                StateManager.addEnvironment(it)
                call.respond(it)
            }
        }
        
        put("/{name}") {
            val name = call.parameters["name"] ?: return@put call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            val environment = call.receive<EnvironmentDto>()
            if (environment.name != name) {
                return@put call.respondText("Environment name mismatch", status = HttpStatusCode.BadRequest)
            }
            if (!JsonValidator.isValidJson(environment.configuration)) {
                return@put call.respondText("Invalid JSON configuration", status = HttpStatusCode.BadRequest)
            }
            environment.copy(configuration = JsonValidator.formatJson(environment.configuration)).let {
                if (StateManager.updateEnvironment(it)) {
                    call.respond(it)
                } else {
                    call.respondText("Environment not found", status = HttpStatusCode.NotFound)
                }
            }
        }
        
        delete("/{name}") {
            val name = call.parameters["name"] ?: return@delete call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            if (StateManager.deleteEnvironment(name)) {
                call.respond(HttpStatusCode.OK)
            } else {
                call.respondText("Environment not found", status = HttpStatusCode.NotFound)
            }
        }
    }
}