plugins {
    alias(libs.plugins.kotlinJvm)
    alias(libs.plugins.ktor)
    application
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
//    implementation(projects.composeApp) // Ensure dependency on composeApp
    implementation(libs.logback)
    implementation(libs.ktor.serverCore)
    implementation(libs.ktor.serverNetty)
    implementation(libs.ktor.contentNegotiation)
    implementation(libs.ktor.serializationJson)
    implementation(libs.jgit)
    testImplementation(libs.ktor.serverTestHost)
    testImplementation(libs.kotlin.testJunit)
//    jsApp(project(path = it.path, configuration = "jsApp"))
//    wasmApp(project(path = it.path, configuration = "wasmApp"))
//    composeWebApp(project(path = it.path, configuration = "composeWebApp"))
}

tasks.named<Copy>("processResources") {
    val jsBrowserDistribution = project(":composeApp").tasks.named("wasmJsBrowserDevelopmentExecutableDistribution")
    dependsOn(jsBrowserDistribution)
    from(jsBrowserDistribution) {
        into("www")
    }
}


