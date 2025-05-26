package org.rudolf

import dto.*
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json

private val client = HttpClient {
    install(ContentNegotiation) {
        json(Json {
            prettyPrint = true
            isLenient = true
        })
    }
}

// private const val API_URL = "http://localhost:8080"
private const val API_URL = ""

suspend fun fetchBranches(repoUrl: String): List<String> = 
    client.post("$API_URL/branches") {
        contentType(ContentType.Application.Json)
        setBody(repoUrl)
    }.body()

suspend fun fetchReleases(): List<ReleaseDto> = 
    client.get("$API_URL/releases").body()

suspend fun createRelease(release: ReleaseDto) {
    client.post("$API_URL/releases") {
        contentType(ContentType.Application.Json)
        setBody(release)
    }
}

suspend fun deleteRelease(name: String) {
    client.delete("$API_URL/releases/$name")
}

suspend fun updateReleaseState(name: String, state: ReleaseState) {
    client.put("$API_URL/releases/$name/state") {
        contentType(ContentType.Application.Json)
        setBody(state)
    }
}

suspend fun updateReleaseBranches(name: String, branches: List<String>) {
    client.put("$API_URL/releases/$name/branches") {
        contentType(ContentType.Application.Json)
        setBody(branches)
    }
}

suspend fun updateReleaseEnvironment(name: String, environment: String) {
    client.put("$API_URL/releases/$name/environment") {
        contentType(ContentType.Application.Json)
        setBody(environment)
    }
}

suspend fun fetchEnvironments(): List<EnvironmentDto> = 
    client.get("$API_URL/environments").body()

suspend fun createEnvironment(environment: EnvironmentDto) {
    client.post("$API_URL/environments") {
        contentType(ContentType.Application.Json)
        setBody(environment)
    }
}

suspend fun updateEnvironment(name: String, environment: EnvironmentDto) {
    client.put("$API_URL/environments/$name") {
        contentType(ContentType.Application.Json)
        setBody(environment)
    }
}

suspend fun deleteEnvironment(name: String) {
    client.delete("$API_URL/environments/$name")
}
