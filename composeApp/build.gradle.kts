import org.jetbrains.compose.desktop.application.dsl.TargetFormat
import org.jetbrains.kotlin.gradle.ExperimentalWasmDsl
import org.jetbrains.kotlin.gradle.targets.js.webpack.KotlinWebpackConfig

plugins {
    alias(libs.plugins.kotlinMultiplatform)
    alias(libs.plugins.composeMultiplatform)
    alias(libs.plugins.composeCompiler)
}

kotlin {
    @OptIn(ExperimentalWasmDsl::class)
    wasmJs {
        outputModuleName = "composeApp"
        browser {
            val rootDirPath = project.rootDir.path
            val projectDirPath = project.projectDir.path
            commonWebpackConfig {
                outputFileName = "composeApp.js"
                devServer = (devServer ?: KotlinWebpackConfig.DevServer()).apply {
                    static = (static ?: mutableListOf()).apply {
                        // Serve sources to debug inside browser
                        add(rootDirPath)
                        add(projectDirPath)
                    }
                }
            }
        }
        binaries.executable()
    }
    // Ensure production build outputs to a directory for serving
//    tasks.named("browserProductionWebpack") {
//        outputs.dir(file("$buildDir/dist/wasmJs/productionExecutable"))
//    }

    sourceSets {
        
        commonMain.dependencies {
            implementation(compose.runtime)
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.ui)
            implementation(compose.components.resources)
            implementation(compose.components.uiToolingPreview)
            implementation(libs.androidx.lifecycle.viewmodel)
            implementation(libs.androidx.lifecycle.runtimeCompose)
            implementation(projects.shared)
            implementation("io.ktor:ktor-client-core:3.1.3")
            implementation("io.ktor:ktor-client-content-negotiation:3.1.3")
            implementation("io.ktor:ktor-serialization-kotlinx-json:3.1.3")
        }
        commonTest.dependencies {
            implementation(libs.kotlin.test)
        }
    }
}

tasks.matching { it.name.contains("production", ignoreCase = true) }.configureEach {
    enabled = false
}

tasks.named("wasmJsBrowserProductionWebpack") {
    dependsOn(
        "wasmJsDevelopmentExecutableCompileSync", 
        "wasmJsProductionExecutableCompileSync"
    )
}

tasks.named("wasmJsBrowserDevelopmentWebpack") {
    dependsOn(
        "wasmJsDevelopmentExecutableCompileSync", 
        "wasmJsProductionExecutableCompileSync"
    )
}