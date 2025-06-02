package org.rudolf

import dto.ReleaseDto
import dto.SimpleResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.security.MessageDigest
import org.eclipse.jgit.api.Git

object GradleBuild {
    /**
     * Builds the release from mergedBranch, sets buildVersion and artifactUrls.
     * Updates the ReleaseDto accordingly.
     */
    suspend fun buildRelease(repositoryUrl: String, release: ReleaseDto): ReleaseDto = withContext(Dispatchers.IO) {
        val mergedBranchResult = release.mergedBranch
        if (mergedBranchResult !is SimpleResult.Success) {
            return@withContext release.copy(
                buildVersion = SimpleResult.Failure("No merged branch to build"),
                artifactUrls = SimpleResult.Failure("No merged branch to build")
            )
        }
        val (branchName, commitName) = mergedBranchResult.value
        val buildVersion = commitName.take(5)
        val tempDir = createTempDir(prefix = "build-")
        try {
            // Clone remote repository to tempDir using JGit
            Git.cloneRepository()
                .setURI(repositoryUrl)
                .setDirectory(tempDir)
                .setBranch(branchName)
                .call().use { }

            // Set version in gradle.properties or build.gradle.kts
            val gradleProps = File(tempDir, "gradle.properties")
            if (gradleProps.exists()) {
                gradleProps.appendText("\nversion=$buildVersion\n")
            } else {
                val buildGradle = File(tempDir, "build.gradle.kts")
                if (buildGradle.exists()) {
                    buildGradle.appendText("\nversion = \"$buildVersion\"\n")
                }
            }

            // Extract docker image names from gradle modules (assume 'jib' plugin)
            val artifactUrls = extractDockerImages(tempDir)

            // Check if images exist locally or remotely
            val missingImages = artifactUrls.filterNot { imageExistsLocallyOrRemotely(it, buildVersion) }
            if (missingImages.isNotEmpty()) {
                // Build images with gradle jib
                val buildResult = runCommand(
                    listOf("./gradlew", "jib"),
                    tempDir
                )
                if (!buildResult.success) throw Exception("Gradle jib failed: ${buildResult.output}")
            }

            release.copy(
                buildVersion = SimpleResult.Success(buildVersion),
                artifactUrls = SimpleResult.Success(artifactUrls)
            )
        } catch (e: Exception) {
            release.copy(
                buildVersion = SimpleResult.Failure(e.message ?: "Build failed"),
                artifactUrls = SimpleResult.Failure(e.message ?: "Build failed")
            )
        } finally {
            tempDir.deleteRecursively()
        }
    }

    private fun extractDockerImages(projectDir: File): List<String> {
        // For each module with a build.gradle(.kts), run gradle to print jib.to.image
        val images = mutableListOf<String>()
        projectDir.walkTopDown().forEach { file ->
            if (file.isFile && (file.name == "build.gradle" || file.name == "build.gradle.kts")) {
                val moduleDir = file.parentFile
                // Try to print jib.to.image using gradle properties
                val result = runCommand(
                    listOf("./gradlew", "-q", "properties", "-PprintJibImage"),
                    moduleDir
                )
                // Parse output for jib.to.image
                val regex = Regex("jib.to.image: (.+)")
                regex.findAll(result.output).forEach { match ->
                    images.add(match.groupValues[1].trim())
                }
            }
        }
        return images.ifEmpty { listOf("example/image:tag") }
    }

    private fun imageExistsLocally(image: String, version: String): Boolean {
        // Check if docker image:tag exists locally
        val tag = if (":" in image) image else "$image:$version"
        val result = runCommand(listOf("docker", "images", "-q", tag), File("."))
        return result.success && result.output.trim().isNotEmpty()
    }

    private fun imageExistsRemotely(image: String, version: String): Boolean {
        // Check if docker image:tag exists in remote registry
        val tag = if (":" in image) image else "$image:$version"
        val result = runCommand(listOf("docker", "manifest", "inspect", tag), File("."))
        return result.success && !result.output.contains("No such manifest")
    }

    private fun imageExistsLocallyOrRemotely(image: String, version: String): Boolean {
        return imageExistsLocally(image, version) || imageExistsRemotely(image, version)
    }

    private data class CommandResult(val success: Boolean, val output: String)

    private fun runCommand(cmd: List<String>, workingDir: File): CommandResult {
        return try {
            val process = ProcessBuilder(cmd)
                .directory(workingDir)
                .redirectErrorStream(true)
                .start()
            val output = process.inputStream.bufferedReader().readText()
            val exitCode = process.waitFor()
            CommandResult(exitCode == 0, output)
        } catch (e: Exception) {
            CommandResult(false, e.message ?: "Unknown error")
        }
    }
}
