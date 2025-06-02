plugins {
    alias(libs.plugins.kotlinJvm)
    alias(libs.plugins.ktor)
    alias(libs.plugins.kotlinSerialization)
    application
    id("com.google.cloud.tools.jib") version "3.4.0"
    id("org.ajoberstar.grgit") version "5.3.0"
}

group = "org.rudolf"
version = "1.0.0"
application {
    mainClass.set("org.rudolf.ApplicationKt")
    
    val isDevelopment: Boolean = project.ext.has("development")
    applicationDefaultJvmArgs = listOf("-Dio.ktor.development=$isDevelopment")
}

dependencies {
    implementation(projects.shared)
    implementation(libs.logback)
    implementation(libs.ktor.serverCore)
    implementation(libs.ktor.serverNetty)
    implementation(libs.ktor.contentNegotiation)
    implementation(libs.ktor.serializationJson)
    implementation("io.ktor:ktor-server-cors:3.1.3")
    implementation(libs.jgit)
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.2")
    implementation("io.ktor:ktor-server-websockets:2.3.2")
    testImplementation(libs.ktor.serverTestHost)
    testImplementation(libs.kotlin.testJunit)
}

tasks.named<Copy>("processResources") {
    val jsBrowserDistribution = project(":composeApp").tasks.named("wasmJsBrowserDevelopmentExecutableDistribution")
    dependsOn(jsBrowserDistribution)
    from(jsBrowserDistribution) {
        into("www")
    }
}

jib {
    from {
        image = "bellsoft/liberica-openjdk-alpine:22.0.2"
        platforms {
            platform {
                os = "linux"
                architecture = "amd64"
            }
            platform {
                os = "linux"
                architecture = "arm64"
            }
        }
    }
    to {
        image = "registry.rudolf.keenetic.link/brencher"
        tags = setOf(grgit.head().abbreviatedId, "latest")
    }
    container {
        creationTime.set(grgit.head().dateTime.toInstant().toString())
        mainClass = "org.rudolf.ApplicationKt"
        ports = listOf("8080")
    }
}


