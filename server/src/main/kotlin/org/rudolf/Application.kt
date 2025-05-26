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
import kotlinx.serialization.json.Json
import org.rudolf.routes.gitRoutes
import org.rudolf.routes.releaseRoutes
import org.rudolf.routes.environmentRoutes

fun main() {
    embeddedServer(Netty, port = 8080) {
        this.module()
    }.start(wait = true)
}

fun Application.module() {
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
//            get("/") {
//                call.respondText("Ktor: ${Greeting().greet()}")
//            }
    }

}
