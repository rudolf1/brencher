package org.rudolf.routes

import io.ktor.http.*
import io.ktor.server.request.*
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.*
import kotlinx.serialization.*
import org.rudolf.GitService

@Serializable
data class Release(val name: String, val branches: List<String>)

val releases = mutableListOf<Release>()

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
            val release = call.receive<Release>()
            releases.add(release)
            call.respond(release)
        }
        delete("/{name}") {
            val name = call.parameters["name"]
                    ?: return@delete call.respondText("Missing name", status = HttpStatusCode.BadRequest)
            releases.removeIf { it.name == name }
            call.respondText("Release removed")
        }
    }
}