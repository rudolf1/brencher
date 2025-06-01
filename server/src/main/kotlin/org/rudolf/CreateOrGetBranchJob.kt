package org.rudolf

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.eclipse.jgit.api.Git

object CreateOrGetBranchJob {
    /**
     * Merges the given branches, creates/updates auto/<hash> branch, and pushes to remote.
     * Returns Pair(branch name, commit name) or error.
     */
    suspend fun mergeBranchesAndPushAutoBranch(
        git: Git?,
        branches: List<String>,
        gitUsername: String = "",
        gitPassword: String = ""
    ): Result<Pair<String, String>> = withContext(Dispatchers.IO) {
        val repo = git ?: return@withContext Result.failure(Exception("Git repo not initialized"))
        if (branches.isEmpty()) return@withContext Result.failure(Exception("No branches specified"))
        val sortedBranches = branches.sorted().map { "origin/$it" }
        val commitIds = sortedBranches.map { repo.repository.findRef(it)?.objectId?.name ?: error("Branch not found") }
        val hash = java.security.MessageDigest.getInstance("SHA-1")
            .digest(commitIds.joinToString(",").toByteArray())
            .joinToString("") { "%02x".format(it) }
        val autoBranch = "auto/$hash"
        val tempBranch = "temp-merge-$hash"
        try {
            // Fetch latest
            val fetchCommand = repo.fetch()
            if (gitUsername.isNotBlank() && gitPassword.isNotBlank()) {
                val credentialsProvider = org.eclipse.jgit.transport.UsernamePasswordCredentialsProvider(gitUsername, gitPassword)
                fetchCommand.setCredentialsProvider(credentialsProvider)
            }
            fetchCommand.call()
            // Inline isAutoBranchUpToDate logic
            run {
                val repo = git ?: return@run false
                if (branches.isEmpty()) return@run false
                val sortedBranches = branches.sorted()
                val commitIds = sortedBranches.mapNotNull { repo.repository.findRef(it)?.objectId?.name }
                if (commitIds.isEmpty()) return@run false
                val hash = java.security.MessageDigest.getInstance("SHA-1")
                    .digest(commitIds.joinToString(",").toByteArray())
                    .joinToString("") { "%02x".format(it) }
                val autoBranch = "auto/$hash"
                val autoRef = repo.repository.findRef(autoBranch) ?: return@run false
                val revWalk = org.eclipse.jgit.revwalk.RevWalk(repo.repository)
                val autoCommit = revWalk.parseCommit(autoRef.objectId)
                val parentIds = autoCommit.parents.map { it.name }.sorted()
                revWalk.close()
                if (parentIds == commitIds.sorted()) {
                    val commit = repo.repository.findRef(autoBranch)?.objectId?.name
                    if (commit != null) return@withContext Result.success(Pair(autoBranch, commit))
                    return@withContext Result.failure(Exception("auto branch exists but commit not found"))
                }
            }
            // Delete temp branch if exists
            repo.repository.findRef(tempBranch)?.let {
                repo.branchDelete().setBranchNames(tempBranch).setForce(true).call()
            }
            // Create temp branch from first branch
            repo.checkout().setStartPoint(commitIds[0])
                .setName(tempBranch)
                .setCreateBranch(true).call()
            // Merge other branches
            for (branch in sortedBranches.drop(1)) {
                val mergeResult = repo.merge()
                    .include(repo.repository.findRef(branch))
                    .call()
                if (!mergeResult.mergeStatus.isSuccessful) {
                    // Clean up temp branch
                    repo.checkout().setName(sortedBranches[0]).call()
                    repo.branchDelete().setBranchNames(tempBranch).setForce(true).call()
                    return@withContext Result.failure(Exception("Merge conflict on branch $branch: \\${mergeResult.toString()}"))
                }
            }
            // Create or update auto/<hash> branch
            repo.branchCreate().setName(autoBranch).setForce(true).call()
            repo.checkout().setName(autoBranch).call()
            // Push auto branch
            val pushCommand = repo.push().setRemote("origin").add(autoBranch).setForce(true)
            if (gitUsername.isNotBlank() && gitPassword.isNotBlank()) {
                val credentialsProvider = org.eclipse.jgit.transport.UsernamePasswordCredentialsProvider(gitUsername, gitPassword)
                pushCommand.setCredentialsProvider(credentialsProvider)
            }
            pushCommand.call()
            // Clean up temp branch
            repo.checkout().setName(sortedBranches[0]).call()
            repo.branchDelete().setBranchNames(tempBranch).setForce(true).call()
            val commit = repo.repository.findRef(autoBranch)?.objectId?.name
            if (commit != null) return@withContext Result.success(Pair(autoBranch, commit))
            return@withContext Result.failure(Exception("auto branch created but commit not found"))
        } catch (e: Exception) {
            return@withContext Result.failure(e)
        }
    }
}
