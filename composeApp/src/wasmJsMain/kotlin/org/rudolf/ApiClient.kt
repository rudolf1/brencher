package org.rudolf

import dto.*
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.client.statement.*
import io.ktor.util.*
import kotlinx.serialization.json.Json

private val client = HttpClient {
    install(ContentNegotiation) {
        json(Json {
            prettyPrint = true
            isLenient = true
        })
    }
}

private const val API_URL = "http://localhost:8080"
// private const val API_URL = ""

suspend fun fetchBranches(repoUrl: String): List<String> = 
    client.get("$API_URL/branches").let { response ->
        if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
        response.body()
    }

suspend fun fetchReleases(): List<ReleaseDto> = 
    client.get("$API_URL/releases").let { response ->
        if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
        response.body()
    }

suspend fun createRelease(release: ReleaseDto) {
    val response = client.post("$API_URL/releases") {
        contentType(ContentType.Application.Json)
        setBody(release)
    }
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun deleteRelease(name: String) {
    val response = client.delete("$API_URL/releases/$name")
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun updateReleaseState(name: String, state: ReleaseState) {
    val response = client.put("$API_URL/releases/$name/state") {
        contentType(ContentType.Application.Json)
        setBody(state)
    }
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun updateReleaseBranches(name: String, branches: List<String>) {
    val response = client.put("$API_URL/releases/$name/branches") {
        contentType(ContentType.Application.Json)
        setBody(branches)
    }
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun updateReleaseEnvironment(name: String, environment: String) {
    val response = client.put("$API_URL/releases/$name/environment") {
        contentType(ContentType.Application.Json)
        setBody(environment)
    }
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun fetchEnvironments(): List<EnvironmentDto> = 
    client.get("$API_URL/environments").let { response ->
        if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
        response.body()
    }

suspend fun createEnvironment(environment: EnvironmentDto) {
    val response = client.post("$API_URL/environments") {
        contentType(ContentType.Application.Json)
        setBody(environment)
    }
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun updateEnvironment(name: String, environment: EnvironmentDto) {
    val response = client.put("$API_URL/environments/$name") {
        contentType(ContentType.Application.Json)
        setBody(environment)
    }
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}

suspend fun deleteEnvironment(name: String) {
    val response = client.delete("$API_URL/environments/$name")
    if (!response.status.isSuccess()) throw Exception(response.bodyAsText())
}
